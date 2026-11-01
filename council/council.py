#!/usr/bin/env python3
"""auto-mediator council — a minimal, zero-dependency multi-agent debate runner.

Escalation path for high-stakes decisions (see COUNCIL.md). Stages: independent analysis ->
anonymous peer review -> synthesis by a chair. `deliberate()` is the reusable entry point.

Cost/latency controls:
  - stage calls run in PARALLEL (threads over blocking I/O) -> ~N x less wall-time;
  - EARLY STOP: if the independent round already reaches a verdict consensus, skip review+synthesis;
  - BUDGET: optional max_calls / max_tokens in the config cap an intervention;
  - a token/call METER (reset_meter/get_meter) exposes real cost for telemetry.
Optional functional ROLES (proposer / critic / verifier) instead of same-prompt diversity.

Stdlib only (Python 3.8+). Reference template — read it, adapt it.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

_METER = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}


def reset_meter():
    _METER.update(calls=0, prompt_tokens=0, completion_tokens=0)


def get_meter() -> dict:
    return dict(_METER)


def call_model(m: dict, messages: list, temperature: float, timeout: int, retries: int = 1) -> str:
    """POST to an OpenAI-compatible /chat/completions endpoint. Returns the text, or raises.

    Retries only transient 5xx (once); does NOT retry 4xx (won't fix itself) or timeouts/URL errors
    (a slow or down model should fail fast, not be waited on N times). Updates the cost meter.
    """
    key = os.environ.get(m.get("api_key_env", ""), "")
    body = json.dumps({"model": m["model"], "messages": messages, "temperature": temperature}).encode()
    req = urllib.request.Request(
        m["base_url"].rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == retries:
                raise
            time.sleep(1.0)
            continue
        u = data.get("usage") or {}
        _METER["calls"] += 1
        _METER["prompt_tokens"] += u.get("prompt_tokens", 0) or 0
        _METER["completion_tokens"] += u.get("completion_tokens", 0) or 0
        return data["choices"][0]["message"]["content"].strip()


def ask(m: dict, prompt: str, cfg: dict) -> str:
    return call_model(m, [{"role": "user", "content": prompt}],
                      cfg.get("temperature", 0.3), cfg.get("timeout_seconds", 60))


def _log(verbose, *a, **k):
    if verbose:
        print(*a, **k)


def _over_budget(cfg: dict) -> bool:
    mc, mt = cfg.get("max_calls"), cfg.get("max_tokens")
    if mc and _METER["calls"] >= mc:
        return True
    if mt and (_METER["prompt_tokens"] + _METER["completion_tokens"]) >= mt:
        return True
    return False


def _parallel(models: list, prompt_for, cfg: dict, verbose: bool, label: str) -> dict:
    out = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(models))) as ex:
        futs = {ex.submit(ask, m, prompt_for(m), cfg): m for m in models}
        for f in concurrent.futures.as_completed(futs):
            m = futs[f]
            try:
                out[m["name"]] = f.result()
                _log(verbose, f"  [{m['name']}] {label} ok")
            except Exception as e:  # noqa: BLE001
                print(f"  [{m['name']}] {label} FAILED: {type(e).__name__}", file=sys.stderr)
    return out


ROLE_PROMPTS = {
    "proposer": "Act as the PROPOSER: argue for the best answer and justify it with the strongest reasons.",
    "critic": "Act as the CRITIC / red-team: attack the likely answer — find errors, risks, counterexamples, and the flaw in its premise if any.",
    "verifier": "Act as the VERIFIER: check the key claims and evidence; flag anything unsupported or that an external check would settle.",
}


def stage_independent(models, question, cfg, verbose=True, roles=False) -> dict:
    _log(verbose, "\n=== Stage 1: independent analysis ===")
    base = (f"Analyze this decision/question and give your reasoned verdict.\n\n{question}\n\n"
            "Be concrete. State the single piece of evidence that would most change your verdict.")
    if roles:
        rv = list(ROLE_PROMPTS.values())
        assign = {m["name"]: rv[i % len(rv)] for i, m in enumerate(models)}
        prompt_for = lambda m: base + "\n\n" + assign[m["name"]]  # noqa: E731
    else:
        prompt_for = lambda m: base  # noqa: E731
    return _parallel(models, prompt_for, cfg, verbose, "analysis")


def stage_review(models, question, answers, cfg, verbose=True) -> dict:
    _log(verbose, "\n=== Stage 2: anonymous peer review ===")
    items = list(answers.items())
    random.shuffle(items)
    labels = [chr(65 + i) for i in range(len(items))]
    anon = "\n\n".join(f"Response {lab}:\n{t}" for lab, (_, t) in zip(labels, items))
    prompt = (f"Question:\n{question}\n\nAnonymous responses from several advisors:\n\n{anon}\n\n"
              "Critique them: which reasoning is strongest vs weakest and why; flag unsupported claims or "
              "ones an external check would settle; then rank them best to worst.")
    return _parallel(models, lambda m: prompt, cfg, verbose, "review")


def stage_synthesis(chair, question, answers, reviews, cfg, verbose=True, final_format=None) -> str:
    _log(verbose, f"\n=== Stage 3: synthesis (chair = {chair['name']}) ===")
    ans = "\n\n".join(f"- {n}: {t}" for n, t in answers.items())
    rev = "\n\n".join(f"- {n}: {t}" for n, t in reviews.items()) if reviews else "(no peer reviews)"
    prompt = (f"You chair a council. Question:\n{question}\n\nAdvisors' analyses:\n{ans}\n\n"
              f"Advisors' peer reviews:\n{rev}\n\n"
              "Write the final verdict: (1) recommendation and confidence, (2) where the council AGREED, "
              "(3) where it SPLIT and why, (4) the cheapest evidence that would settle the split. "
              "Do not paper over disagreement.")
    if final_format:
        prompt += f"\n\nEnd your answer with EXACTLY these lines:\n{final_format}"
    return ask(chair, prompt, cfg)


def _field(text, name):
    m = re.search(rf"{name}:\s*(.+)", text)
    return m.group(1).strip() if m else ""


def _consensus(answers: dict):
    """If every answer that states a VERDICT states the SAME one, return it; else None."""
    vs = [_field(t, "VERDICT").upper() for t in answers.values()]
    vs = [re.sub(r"[^A-Z\- ]", "", v).strip() for v in vs if v]
    return vs[0] if len(vs) >= 2 and len(set(vs)) == 1 else None


def _consensus_result(answers: dict, verdict: str) -> str:
    reason = next((_field(t, "KEY_REASON") for t in answers.values() if _field(t, "KEY_REASON")), "consensus")
    confs = [int(c) for t in answers.values() if (c := _field(t, "CONFIDENCE")).isdigit()]
    conf = round(sum(confs) / len(confs)) if confs else 80
    return (f"Round-1 consensus (no debate needed).\nVERDICT: {verdict}\n"
            f"KEY_REASON: {reason}\nCONFIDENCE: {conf}")


def deliberate(models, question, cfg, chair, verbose=True, final_format=None,
               roles=False, early_stop=True) -> str:
    """Full council with parallel stages, early-stop on consensus, and budget cap. Returns synthesis text."""
    q1 = question + (f"\n\n{final_format}" if final_format else "")
    answers = stage_independent(models, q1, cfg, verbose, roles)
    if not answers:
        raise RuntimeError("no models answered")
    if early_stop and final_format and (v := _consensus(answers)):
        _log(verbose, f"  [early-stop] round-1 consensus: {v} (skipped review + synthesis)")
        return _consensus_result(answers, v)
    reviews = {} if _over_budget(cfg) or len(answers) < 2 else stage_review(models, question, answers, cfg, verbose)
    return stage_synthesis(chair, question, answers, reviews, cfg, verbose, final_format)


def pick_chair(models, cfg):
    return next((m for m in models if m["name"] == cfg.get("chair")), models[0])


def main() -> int:
    p = argparse.ArgumentParser(description="auto-mediator multi-agent council")
    p.add_argument("question")
    p.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "config.json"))
    p.add_argument("--roles", action="store_true", help="assign proposer/critic/verifier roles in round 1")
    args = p.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)
    models = cfg["models"]
    if len(models) < 2:
        print("A council needs at least 2 models.", file=sys.stderr)
        return 2
    reset_meter()
    try:
        verdict = deliberate(models, args.question, cfg, pick_chair(models, cfg), verbose=True, roles=args.roles)
    except RuntimeError as e:
        print(f"Council could not run: {e}", file=sys.stderr)
        return 1
    mt = get_meter()
    print("\n" + "=" * 60 + "\nCOUNCIL VERDICT\n" + "=" * 60)
    print(verdict)
    print(f"\n[cost] {mt['calls']} calls, {mt['prompt_tokens']+mt['completion_tokens']} tokens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

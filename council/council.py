#!/usr/bin/env python3
"""auto-mediator council — a minimal, zero-dependency multi-agent debate runner.

Escalation path for high-stakes decisions (see COUNCIL.md). Runs any set of
OpenAI-compatible chat models through three stages: independent analysis ->
anonymous peer review -> synthesis by a chair.

`deliberate()` is the reusable entry point (quiet when verbose=False) so other
tools — e.g. the eval harness — can use the council as a solver.

Stdlib only (Python 3.8+). Reference template — read it, adapt it.

Usage:
    cp config.example.json config.json   # edit with your models
    export OPENAI_API_KEY=...            # and any other keys your config names
    python council.py "Your decision or question here"
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request


def call_model(m: dict, messages: list, temperature: float, timeout: int, retries: int = 2) -> str:
    """POST to an OpenAI-compatible /chat/completions endpoint. Returns the text, or raises.

    Retries transient failures (timeouts and 5xx) with a short backoff; does NOT retry
    4xx (wrong model, bad auth) since those won't fix themselves. Reasoning models can be
    slow, so give them a generous `timeout` in the config.
    """
    key = os.environ.get(m.get("api_key_env", ""), "")
    body = json.dumps({"model": m["model"], "messages": messages, "temperature": temperature}).encode()
    req = urllib.request.Request(
        m["base_url"].rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode())
            return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == retries:  # client error, or out of retries
                raise
            last_err = e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries:
                raise
            last_err = e
        time.sleep(1.5 * (attempt + 1))
    raise last_err  # pragma: no cover


def ask(m: dict, prompt: str, cfg: dict) -> str:
    return call_model(
        m,
        [{"role": "user", "content": prompt}],
        cfg.get("temperature", 0.3),
        cfg.get("timeout_seconds", 120),
    )


def _log(verbose: bool, *a, **k):
    if verbose:
        print(*a, **k)


def stage_independent(models: list, question: str, cfg: dict, verbose: bool = True) -> dict:
    _log(verbose, "\n=== Stage 1: independent analysis ===")
    out = {}
    prompt = (
        f"Analyze this decision/question independently and give your reasoned verdict.\n\n{question}\n\n"
        "Be concrete. State your verdict, your confidence, and the single piece of evidence that would most change it."
    )
    for m in models:
        try:
            out[m["name"]] = ask(m, prompt, cfg)
            _log(verbose, f"  [{m['name']}] ok ({len(out[m['name']])} chars)")
        except (urllib.error.URLError, KeyError, TimeoutError) as e:
            print(f"  [{m['name']}] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
    return out


def stage_review(models: list, question: str, answers: dict, cfg: dict, verbose: bool = True) -> dict:
    """Each model reviews all answers, anonymized and shuffled."""
    _log(verbose, "\n=== Stage 2: anonymous peer review ===")
    items = list(answers.items())
    random.shuffle(items)
    labels = [chr(ord("A") + i) for i in range(len(items))]
    anon = "\n\n".join(f"Response {lab}:\n{txt}" for lab, (_, txt) in zip(labels, items))
    reviews = {}
    prompt = (
        f"Question:\n{question}\n\nHere are anonymous responses from several advisors:\n\n{anon}\n\n"
        "Critique them. Which reasoning is strongest and which is weakest, and why? "
        "Flag any claim that is unsupported or that an external check would settle. Then rank them best to worst."
    )
    for m in models:
        try:
            reviews[m["name"]] = ask(m, prompt, cfg)
            _log(verbose, f"  [{m['name']}] reviewed")
        except (urllib.error.URLError, KeyError, TimeoutError) as e:
            print(f"  [{m['name']}] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
    return reviews


def stage_synthesis(chair: dict, question: str, answers: dict, reviews: dict, cfg: dict,
                    verbose: bool = True, final_format: str | None = None) -> str:
    _log(verbose, f"\n=== Stage 3: synthesis (chair = {chair['name']}) ===")
    ans = "\n\n".join(f"- {n}: {t}" for n, t in answers.items())
    rev = "\n\n".join(f"- {n}: {t}" for n, t in reviews.items()) if reviews else "(no peer reviews)"
    prompt = (
        f"You chair a council. Question:\n{question}\n\nAdvisors' analyses:\n{ans}\n\n"
        f"Advisors' peer reviews:\n{rev}\n\n"
        "Write the final verdict. State clearly: (1) the recommendation and confidence, "
        "(2) where the council AGREED, (3) where it SPLIT and why, "
        "(4) the cheapest evidence that would settle the split. Do not paper over disagreement."
    )
    if final_format:
        prompt += f"\n\nEnd your answer with EXACTLY these lines:\n{final_format}"
    return ask(chair, prompt, cfg)


def deliberate(models: list, question: str, cfg: dict, chair: dict,
               verbose: bool = True, final_format: str | None = None) -> str:
    """Full 3-stage council. Returns the chair's synthesis. Degrades if some models fail."""
    answers = stage_independent(models, question, cfg, verbose)
    if not answers:
        raise RuntimeError("no models answered")
    reviews = stage_review(models, question, answers, cfg, verbose) if len(answers) >= 2 else {}
    return stage_synthesis(chair, question, answers, reviews, cfg, verbose, final_format)


def pick_chair(models: list, cfg: dict) -> dict:
    return next((m for m in models if m["name"] == cfg.get("chair")), models[0])


def main() -> int:
    p = argparse.ArgumentParser(description="auto-mediator multi-agent council")
    p.add_argument("question", help="the decision or question to put to the council")
    p.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "config.json"))
    args = p.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)
    models = cfg["models"]
    if len(models) < 2:
        print("A council needs at least 2 models. Edit your config.", file=sys.stderr)
        return 2
    chair = pick_chair(models, cfg)

    try:
        verdict = deliberate(models, args.question, cfg, chair, verbose=True)
    except RuntimeError as e:
        print(f"Council could not run: {e}", file=sys.stderr)
        return 1

    print("\n" + "=" * 60 + "\nCOUNCIL VERDICT\n" + "=" * 60)
    print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

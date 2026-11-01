#!/usr/bin/env python3
"""auto-mediator eval harness v1 — measure reasoning quality on held-out cases, oracle-scored.

Each case has a KNOWN answer and a parseable VERDICT, so scoring is deterministic (not an LLM
judging vibes). Lets you vary transversal parameters and measure their effect on the whole suite:
  - which model        (--model / --base-url / --api-key-env)
  - inference budget    (--samples N  -> self-consistency majority vote)
  - ensemble heterogeneity (--council config.json -> a cross-lineage council as the solver)

Stdlib only; reuses the council's OpenAI-compatible client and deliberation.

Usage:
    export OPENAI_API_KEY=...
    python eval/run_eval.py --model gpt-4o-mini
    python eval/run_eval.py --model gpt-4o-mini --samples 5 --temperature 0.7
    python eval/run_eval.py --council council/config.json     # cross-lineage council solver

HONEST LIMITS: the verdict oracle is robust; the reason check is keyword-based (approximate).
Do NOT tune prompts on these cases and then report on them — that overfits. Keep a held-out split.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "council"))
from council import call_model, deliberate, pick_chair  # noqa: E402

FORMAT = (
    "\n\nReason briefly, then end with EXACTLY these three lines:\n"
    "VERDICT: <one of: {opts}>\nKEY_REASON: <one short phrase>\nCONFIDENCE: <0-100>"
)


def parse(out: str):
    v = re.search(r"VERDICT:\s*([A-Za-z\- ]+)", out)
    r = re.search(r"KEY_REASON:\s*(.+)", out)
    c = re.search(r"CONFIDENCE:\s*(\d{1,3})", out)
    return (
        (v.group(1).strip().upper() if v else ""),
        (r.group(1).strip() if r else ""),
        (min(100, int(c.group(1))) if c else None),
    )


def has_token(text: str, token: str) -> bool:
    return re.search(r"\b" + re.escape(token.upper()) + r"\b", text.upper()) is not None


def to_option(verdict: str, opts: list) -> str:
    for o in opts:
        if has_token(verdict, o):
            return o.upper()
    return ""


def solve_single(m, case, samples, temp, timeout):
    """Single model, majority vote if samples>1. Returns (winner, reason_ok, conf, calls)."""
    opts = [case["expected"]] + case["distractors"]
    prompt = case["prompt"] + FORMAT.format(opts=" | ".join(opts))
    votes, confs, reason_hits, calls = collections.Counter(), [], [], 0
    for _ in range(samples):
        calls += 1
        try:
            out = call_model(m, [{"role": "user", "content": prompt}], temp, timeout)
        except Exception as e:  # noqa: BLE001
            print(f"    call failed: {type(e).__name__}", file=sys.stderr)
            continue
        verdict, reason, conf = parse(out)
        tok = to_option(verdict, opts)
        if tok:
            votes[tok] += 1
        if conf is not None:
            confs.append(conf)
        if case.get("reason_must_include"):
            reason_hits.append(bool(re.search(case["reason_must_include"], reason)))
    winner = votes.most_common(1)[0][0] if votes else ""
    conf = (sum(confs) / len(confs)) if confs else None
    reason_ok = (any(reason_hits) if reason_hits else None)
    return winner, reason_ok, conf, calls


def solve_council(models, chair, cfg, case):
    """A cross-lineage council as the solver. Returns (winner, reason_ok, conf, calls)."""
    opts = [case["expected"]] + case["distractors"]
    fmt = FORMAT.format(opts=" | ".join(opts)).strip()
    calls = len(models) * 2 + 1  # approx: N independent + N review + 1 synthesis
    try:
        synth = deliberate(models, case["prompt"], cfg, chair, verbose=False, final_format=fmt)
    except Exception as e:  # noqa: BLE001
        print(f"    council failed: {type(e).__name__}", file=sys.stderr)
        return "", None, None, calls
    verdict, reason, conf = parse(synth)
    winner = to_option(verdict, opts)
    reason_ok = None
    if case.get("reason_must_include"):
        reason_ok = bool(re.search(case["reason_must_include"], reason))
    return winner, reason_ok, conf, calls


def main() -> int:
    p = argparse.ArgumentParser(description="auto-mediator eval harness v1")
    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--base-url", default="https://api.openai.com/v1")
    p.add_argument("--api-key-env", default="OPENAI_API_KEY")
    p.add_argument("--samples", type=int, default=1, help="self-consistency: majority vote over N")
    p.add_argument("--temperature", type=float, default=0.3)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--council", default=None, help="path to a council config.json -> use the council as solver")
    p.add_argument("--cases", default=os.path.join(os.path.dirname(__file__), "cases.jsonl"))
    p.add_argument("--ids", default=None, help="comma-separated case ids to run a subset")
    args = p.parse_args()

    cases = [json.loads(ln) for ln in open(args.cases) if ln.strip()]
    if args.ids:
        want = {s.strip() for s in args.ids.split(",")}
        cases = [c for c in cases if c["id"] in want]

    if args.council:
        with open(args.council) as f:
            cfg = json.load(f)
        c_models = cfg["models"]
        chair = pick_chair(c_models, cfg)
        label = f"council [{', '.join(m['name'] for m in c_models)}], chair={chair['name']}"
        solver = lambda case: solve_council(c_models, chair, cfg, case)  # noqa: E731
    else:
        m = {"model": args.model, "base_url": args.base_url, "api_key_env": args.api_key_env}
        label = f"model={args.model} samples={args.samples} temp={args.temperature}"
        solver = lambda case: solve_single(m, case, args.samples, args.temperature, args.timeout)  # noqa: E731

    print(f"Suite: {len(cases)} cases | {label}\n")

    by_cat = collections.defaultdict(lambda: [0, 0])
    n_correct = reason_num = reason_den = 0
    brier, brier_n, conf_correct, conf_wrong, calls_total = 0.0, 0, [], [], 0
    t0 = time.time()
    for c in cases:
        winner, reason_ok, conf, calls = solver(c)
        calls_total += calls
        correct = winner == c["expected"].upper()
        n_correct += correct
        by_cat[c["category"]][0] += correct
        by_cat[c["category"]][1] += 1
        if reason_ok is not None:
            reason_den += 1
            reason_num += bool(reason_ok)
        if conf is not None:
            brier += (conf / 100.0 - (1.0 if correct else 0.0)) ** 2
            brier_n += 1
            (conf_correct if correct else conf_wrong).append(conf)
        mark = "ok " if correct else "XX "
        rtag = "" if reason_ok is None else (" reason:ok" if reason_ok else " reason:miss")
        print(f"  {mark}{c['id']:20s} -> {winner or '(unparsed)':12s} exp={c['expected']:12s}"
              f" conf={conf if conf is not None else '-'}{rtag}")

    dt = time.time() - t0
    print(f"\n=== ACCURACY: {n_correct}/{len(cases)} = {n_correct/len(cases)*100:.0f}% ===")
    print("por categoría:")
    for cat, (ok, tot) in sorted(by_cat.items()):
        print(f"  {cat:22s} {ok}/{tot}")
    if reason_den:
        print(f"right-for-right-reason: {reason_num}/{reason_den} = {reason_num/reason_den*100:.0f}%")
    if brier_n:
        mc = (sum(conf_correct) / len(conf_correct)) if conf_correct else float("nan")
        mw = (sum(conf_wrong) / len(conf_wrong)) if conf_wrong else float("nan")
        print(f"calibration: Brier={brier/brier_n:.3f} | mean conf correct={mc:.0f} vs wrong={mw:.0f}"
              f"  (small/negative gap = overconfident)")
    print(f"cost: {calls_total} model calls in {dt:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

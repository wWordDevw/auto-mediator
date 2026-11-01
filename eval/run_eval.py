#!/usr/bin/env python3
"""auto-mediator eval harness v0 — measure reasoning quality on held-out cases, oracle-scored.

Each case has a KNOWN answer and a parseable VERDICT, so scoring is deterministic (not an LLM
judging vibes). Lets you vary transversal parameters and measure their effect on the whole suite:
  - which model        (--model / --base-url / --api-key-env)
  - inference budget    (--samples N  -> self-consistency majority vote)

Stdlib only; reuses the council's OpenAI-compatible client.

Usage:
    export OPENAI_API_KEY=...
    python eval/run_eval.py --model gpt-4o-mini
    python eval/run_eval.py --model gpt-4o-mini --samples 5 --temperature 0.7
    python eval/run_eval.py --model gpt-4o --base-url https://api.openai.com/v1

HONEST LIMITS (v0): 10 cases is a skeleton, not a benchmark. The verdict oracle is robust but the
reason check is keyword-based (approximate). Do NOT tune prompts on these cases and then report on
them — that overfits. Grow the suite and keep a held-out split.
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
from council import call_model  # noqa: E402

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


def solve(m, case, samples, temp, timeout):
    """Return (verdict_token, reason_ok, confidence, n_calls). Majority vote if samples>1."""
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
        for o in opts:                       # map this sample's verdict to an option token
            if has_token(verdict, o):
                votes[o.upper()] += 1
                break
        if conf is not None:
            confs.append(conf)
        if case.get("reason_must_include"):
            reason_hits.append(bool(re.search(case["reason_must_include"], reason)))
    winner = votes.most_common(1)[0][0] if votes else ""
    conf = (sum(confs) / len(confs)) if confs else None
    reason_ok = (any(reason_hits) if reason_hits else None)
    return winner, reason_ok, conf, calls


def main() -> int:
    p = argparse.ArgumentParser(description="auto-mediator eval harness v0")
    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--base-url", default="https://api.openai.com/v1")
    p.add_argument("--api-key-env", default="OPENAI_API_KEY")
    p.add_argument("--samples", type=int, default=1, help="self-consistency: majority vote over N")
    p.add_argument("--temperature", type=float, default=0.3)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--cases", default=os.path.join(os.path.dirname(__file__), "cases.jsonl"))
    args = p.parse_args()

    m = {"model": args.model, "base_url": args.base_url, "api_key_env": args.api_key_env}
    cases = [json.loads(ln) for ln in open(args.cases) if ln.strip()]
    print(f"Suite: {len(cases)} cases | model={args.model} samples={args.samples} temp={args.temperature}\n")

    by_cat = collections.defaultdict(lambda: [0, 0])
    n_correct = reason_num = reason_den = 0
    brier, brier_n, conf_correct, conf_wrong, calls_total = 0.0, 0, [], [], 0
    t0 = time.time()
    for c in cases:
        winner, reason_ok, conf, calls = solve(m, c, args.samples, args.temperature, args.timeout)
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
        print(f"  {mark}{c['id']:18s} -> {winner or '(unparsed)':12s} exp={c['expected']:12s}"
              f" conf={conf if conf is not None else '-'}{rtag}")

    dt = time.time() - t0
    print(f"\n=== ACCURACY: {n_correct}/{len(cases)} = {n_correct/len(cases)*100:.0f}% ===")
    print("por categoría:")
    for cat, (ok, tot) in sorted(by_cat.items()):
        print(f"  {cat:22s} {ok}/{tot}")
    if reason_den:
        print(f"right-for-right-reason: {reason_num}/{reason_den} = {reason_num/reason_den*100:.0f}%")
    if brier_n:
        print(f"calibration: Brier={brier/brier_n:.3f} | mean conf correct="
              f"{(sum(conf_correct)/len(conf_correct)) if conf_correct else float('nan'):.0f}"
              f" vs wrong={(sum(conf_wrong)/len(conf_wrong)) if conf_wrong else float('nan'):.0f}"
              f"  (gap<0 or tiny = overconfident)")
    print(f"cost: {calls_total} model calls in {dt:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

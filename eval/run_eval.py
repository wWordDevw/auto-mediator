#!/usr/bin/env python3
"""auto-mediator eval harness — measure reasoning quality on held-out cases, oracle-scored.

Varies transversal parameters and measures their effect on the whole suite:
  - which model             (--model / --base-url / --api-key-env)
  - inference budget         (--samples N  -> self-consistency majority vote)
  - ensemble heterogeneity   (--council config.json  -> cross-lineage council)
  - functional roles         (--roles, with --council  -> proposer/critic/verifier instead of same prompt)

Reports accuracy (per category), right-for-right-reason, calibration, and real COST (calls + tokens)
from the council meter. Stdlib only.

HONEST LIMITS: verdict oracle is robust; the reason check is keyword-based (approximate). Keep a
held-out split; don't tune prompts on these cases and then report on them.
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
from council import call_model, deliberate, pick_chair, get_meter  # noqa: E402

FORMAT = ("VERDICT: <one of: {opts}>\nKEY_REASON: <one short phrase>\nCONFIDENCE: <0-100>")
ASK = "\n\nReason briefly, then end with EXACTLY these three lines:\n" + FORMAT


def parse(out):
    v = re.search(r"VERDICT:\s*([A-Za-z\- ]+)", out)
    r = re.search(r"KEY_REASON:\s*(.+)", out)
    c = re.search(r"CONFIDENCE:\s*(\d{1,3})", out)
    return ((v.group(1).strip().upper() if v else ""), (r.group(1).strip() if r else ""),
            (min(100, int(c.group(1))) if c else None))


def has_token(text, token):
    return re.search(r"\b" + re.escape(token.upper()) + r"\b", text.upper()) is not None


def to_option(verdict, opts):
    return next((o.upper() for o in opts if has_token(verdict, o)), "")


def solve_single(m, case, samples, temp, timeout):
    opts = [case["expected"]] + case["distractors"]
    prompt = case["prompt"] + ASK.format(opts=" | ".join(opts))
    votes, confs, reason_hits = collections.Counter(), [], []
    for _ in range(samples):
        try:
            out = call_model(m, [{"role": "user", "content": prompt}], temp, timeout)
        except Exception as e:  # noqa: BLE001
            print(f"    call failed: {type(e).__name__}", file=sys.stderr)
            continue
        v, reason, conf = parse(out)
        if (tok := to_option(v, opts)):
            votes[tok] += 1
        if conf is not None:
            confs.append(conf)
        if case.get("reason_must_include"):
            reason_hits.append(bool(re.search(case["reason_must_include"], reason)))
    winner = votes.most_common(1)[0][0] if votes else ""
    return winner, (any(reason_hits) if reason_hits else None), (sum(confs) / len(confs) if confs else None)


def solve_council(models, chair, cfg, case, roles):
    opts = [case["expected"]] + case["distractors"]
    fmt = ASK.strip().format(opts=" | ".join(opts))
    try:
        synth = deliberate(models, case["prompt"], cfg, chair, verbose=False, final_format=fmt, roles=roles)
    except Exception as e:  # noqa: BLE001
        print(f"    council failed: {type(e).__name__}", file=sys.stderr)
        return "", None, None
    v, reason, conf = parse(synth)
    reason_ok = bool(re.search(case["reason_must_include"], reason)) if case.get("reason_must_include") else None
    return to_option(v, opts), reason_ok, conf


def main() -> int:
    p = argparse.ArgumentParser(description="auto-mediator eval harness")
    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--base-url", default="https://api.openai.com/v1")
    p.add_argument("--api-key-env", default="OPENAI_API_KEY")
    p.add_argument("--samples", type=int, default=1)
    p.add_argument("--temperature", type=float, default=0.3)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--council", default=None, help="council config.json -> use the council as solver")
    p.add_argument("--roles", action="store_true", help="with --council: proposer/critic/verifier roles")
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
        c_models, chair = cfg["models"], pick_chair(cfg["models"], cfg)
        label = f"council [{', '.join(m['name'] for m in c_models)}] roles={args.roles}"
        solver = lambda c: solve_council(c_models, chair, cfg, c, args.roles)  # noqa: E731
    else:
        m = {"model": args.model, "base_url": args.base_url, "api_key_env": args.api_key_env}
        label = f"model={args.model} samples={args.samples}"
        solver = lambda c: solve_single(m, c, args.samples, args.temperature, args.timeout)  # noqa: E731

    print(f"Suite: {len(cases)} cases | {label}\n")
    by_cat = collections.defaultdict(lambda: [0, 0])
    n_correct = reason_num = reason_den = 0
    brier = brier_n = calls0 = tok0 = 0
    conf_correct, conf_wrong = [], []
    base = get_meter()
    calls0, tok0 = base["calls"], base["prompt_tokens"] + base["completion_tokens"]
    t0 = time.time()
    for c in cases:
        winner, reason_ok, conf = solver(c)
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
    mt = get_meter()
    calls = mt["calls"] - calls0
    toks = (mt["prompt_tokens"] + mt["completion_tokens"]) - tok0
    n = len(cases)
    print(f"\n=== ACCURACY: {n_correct}/{n} = {n_correct/n*100:.0f}% ===")
    for cat, (ok, tot) in sorted(by_cat.items()):
        print(f"  {cat:22s} {ok}/{tot}")
    if reason_den:
        print(f"right-for-right-reason: {reason_num}/{reason_den} = {reason_num/reason_den*100:.0f}%")
    if brier_n:
        mc = sum(conf_correct) / len(conf_correct) if conf_correct else float("nan")
        mw = sum(conf_wrong) / len(conf_wrong) if conf_wrong else float("nan")
        print(f"calibration: Brier={brier/brier_n:.3f} | conf correct={mc:.0f} vs wrong={mw:.0f}")
    print(f"cost: {calls} calls, {toks} tokens ({toks//max(1,n)}/case) in {dt:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

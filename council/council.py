#!/usr/bin/env python3
"""auto-mediator council — a minimal, zero-dependency multi-agent debate runner.

Escalation path for high-stakes decisions (see COUNCIL.md). Runs any set of
OpenAI-compatible chat models through three stages: independent analysis ->
anonymous peer review -> synthesis by a chair.

Stdlib only (Python 3.8+). Reference template — read it, adapt it.

Usage:
    cp config.example.json config.json   # edit with your models
    export OPENAI_API_KEY=...            # and any other keys your config names
    python council.py "Your decision or question here"
    python council.py --config config.json "..."
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.error
import urllib.request


def call_model(m: dict, messages: list, temperature: float, timeout: int) -> str:
    """POST to an OpenAI-compatible /chat/completions endpoint. Returns the text, or raises."""
    key = os.environ.get(m.get("api_key_env", ""), "")
    body = json.dumps({"model": m["model"], "messages": messages, "temperature": temperature}).encode()
    req = urllib.request.Request(
        m["base_url"].rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"].strip()


def ask(m: dict, prompt: str, cfg: dict) -> str:
    return call_model(
        m,
        [{"role": "user", "content": prompt}],
        cfg.get("temperature", 0.3),
        cfg.get("timeout_seconds", 120),
    )


def stage_independent(models: list, question: str, cfg: dict) -> dict:
    print("\n=== Stage 1: independent analysis ===")
    out = {}
    prompt = (
        f"Analyze this decision/question independently and give your reasoned verdict.\n\n{question}\n\n"
        "Be concrete. State your verdict, your confidence, and the single piece of evidence that would most change it."
    )
    for m in models:
        try:
            out[m["name"]] = ask(m, prompt, cfg)
            print(f"  [{m['name']}] ok ({len(out[m['name']])} chars)")
        except (urllib.error.URLError, KeyError, TimeoutError) as e:
            print(f"  [{m['name']}] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
    return out


def stage_review(models: list, question: str, answers: dict, cfg: dict) -> dict:
    """Each model reviews all answers, anonymized and shuffled."""
    print("\n=== Stage 2: anonymous peer review ===")
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
            print(f"  [{m['name']}] reviewed")
        except (urllib.error.URLError, KeyError, TimeoutError) as e:
            print(f"  [{m['name']}] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
    return reviews


def stage_synthesis(chair: dict, question: str, answers: dict, reviews: dict, cfg: dict) -> str:
    print(f"\n=== Stage 3: synthesis (chair = {chair['name']}) ===")
    ans = "\n\n".join(f"- {n}: {t}" for n, t in answers.items())
    rev = "\n\n".join(f"- {n}: {t}" for n, t in reviews.items())
    prompt = (
        f"You chair a council. Question:\n{question}\n\nAdvisors' analyses:\n{ans}\n\n"
        f"Advisors' peer reviews:\n{rev}\n\n"
        "Write the final verdict. State clearly: (1) the recommendation and confidence, "
        "(2) where the council AGREED, (3) where it SPLIT and why, "
        "(4) the cheapest evidence that would settle the split. Do not paper over disagreement."
    )
    return ask(chair, prompt, cfg)


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
    chair = next((m for m in models if m["name"] == cfg.get("chair")), models[0])

    answers = stage_independent(models, args.question, cfg)
    if len(answers) < 2:
        print("Fewer than 2 models answered; cannot hold a council.", file=sys.stderr)
        return 1
    reviews = stage_review(models, args.question, answers, cfg)
    verdict = stage_synthesis(chair, args.question, answers, reviews, cfg)

    print("\n" + "=" * 60 + "\nCOUNCIL VERDICT\n" + "=" * 60)
    print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

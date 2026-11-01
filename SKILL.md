---
name: auto-mediator
description: Red-team your OWN verdict before you commit it — and resolve the doubt with evidence, not more thinking. Use before concluding ANY consequential yes/no, go/no-go, "can't / impossible / not supported / won't work", before rejecting a result, before abandoning an approach, OR before an irreversible / costly YES. Catches premature negatives ("no" that should be "yes" or "not yet") AND over-eager positives. Triggers on "red-team this", "devil's advocate", "steelman the opposite", "pre-mortem this", "pressure-test this", "is it really no?", and fires automatically whenever you are about to assert a consequential negative, a hard limit, or commit something irreversible.
---

# auto-mediator — mediate between your snap verdict and the evidence

**The failure it fixes:** closing too early. Declaring "impossible" when it was "not yet",
rejecting a good result over a bad test, or green-lighting a risky call on a hunch.

**Why it works the way it does.** The obvious fix — "just critique your own answer" — backfires:
an agent that self-corrects *without an external signal* usually gets **worse**, flipping correct
answers to wrong ones and rarely spotting its real flaws (Huang et al., ICLR 2024). Self-correction
only pays when there is an **oracle**: running the test, calling another tool, measuring the real
number. So this protocol is **not "think harder" — it is "turn the doubt into a cheap EXTERNAL
check."** Golden rule: **flip a verdict on EVIDENCE, never on more reasoning.**

## When to fire
- Any **yes/no** that changes what you do, spends the user's resources, or closes off a path.
- **Always** before "can't / impossible / not supported / no way / won't work / reject".
- Before **abandoning** an approach, idea, or design.
- Before an **irreversible or costly YES** (there, red-team the YES, not just the NO).
- When the user says *red-team*, *devil's advocate*, *steelman it*, *pre-mortem*, *is it really no?*.
- NOT for reversible trivialities or obvious preferences. **Don't ritualize it** — firing on everything
  dulls it and wastes tokens. Use it where being wrong is expensive.

## The cycle (write it out, don't think it silently) — ONE pass
Produce a short **AUTO-MEDIATOR** block with these 6 lines:

1. **Initial verdict + confidence** (e.g. "NO-GO, 70%").
2. **Steelman the opposite** — the STRONGEST case that the answer is YES / it's possible / it works
   (make it real, not a straw man). Turn it into **2-3 concrete verification questions** whose answer
   would **flip** the verdict (chain-of-verification style). Answer each with evidence, not opinion.
3. **Not tried yet** — concrete tools / routes / approaches you have NOT attempted (see checklists).
4. **Bias that may be pulling me here** (see list).
5. **Cheap evidence that would change it** — what quick data / test / attempt confirms or flips this?
   If it's cheap, **GET IT BEFORE closing.** This is the core: resolve doubt with an oracle, not more text.
6. **Final verdict**: `confirmed` · `changed to "not yet / need X"` · `reversed`. **Only change the verdict
   if the evidence from step 5 warrants it** (not because you re-thought it). Don't close a "no/can't" while
   a cheap untried path remains; don't give a costly YES without passing its premortem (below).

## Premortem for a YES / GO (symmetry — don't only hunt the "no")
Before a costly / irreversible GO: **assume it already blew up 6 months from now — why?** List the plausible
causes (imagining the failure as already-happened raises your hit rate on real causes by ~30%; Klein's
prospective-hindsight). If a cause is cheap to close now (a mis-measured number, a short sample, an untested
regime), close it before the GO.

## Checklist — "I concluded it's IMPOSSIBLE / blocked"
- Another **tool / method** not tried? (a different library, CLI, API, headless browser, public mirror).
- Another **endpoint / route / form** of the same resource? (an embed, a public API, a cache, an export).
- A different **permission / credential** path? (your own creds, ask the user to run it, approve the exact command).
- Was it blocked by a **filter / guardrail** rather than true impossibility? → reframe safely, or escalate to the human.
- Can I **ask the user** for the missing piece instead of declaring it impossible?
- Is it "impossible" or "impossible **the way I tried it**"?

## Checklist — "I'm REJECTING a result / test / analysis as a failure"
- **Units / inputs correct?** A wrong unit, scale, or a placeholder value instead of the real measured one is a
  classic **silent 10× error** that sinks a good result. Verify before you trust the number.
- **Does my implementation match the method being tested?** A failure of the *naive* version doesn't refute the
  *refined* one → often the right verdict is **"not evaluated yet"**, not "doesn't work".
- **Realistic costs / overhead included?** Does the effect exist *before* costs?
- **Any leakage / look-ahead** that would flip the sign?
- **Enough sample and enough regime diversity?** (a short window = provisional).
- **Direction of the test's bias:** a SOLID negative (failed even the lenient version) or a FRAGILE one
  (test too harsh / different from the claim)?

> These two checklists are **templates**. Add your own domain checklist (the failure modes specific to your work)
> and this skill gets sharper over time.

## Biases to name out loud
premature closure · confirmation (seeking data that backs my first "no") · anchoring to the first failed attempt ·
giving up after 1-2 guardrail blocks · cost/overfitting/sample traps when judging a result · assuming the source's
claim is false (or true) without measuring · overconfidence in my own judgment (hence: external evidence).

## Escalate to a multi-agent council
If the fork is **big** (real money, shipping to production, a costly/irreversible decision), one agent debating
itself isn't enough. Escalate to a **multi-agent council**: several independent agents analyze, peer-review each
other, and a chair synthesizes — multiple agents debating beat a single model on reasoning and factuality
(Du et al., 2023). A ready-to-use reference council lives in [`council/`](council/) (optional, provider-agnostic).

## Close the loop (so you don't trip the same way twice)
If the cycle **flipped** a verdict (a "no" that was "yes", a mis-measured input), **record the lesson** — add it
to the checklists above and to wherever you persist notes. That way the protocol learns from each miss.

## Output
First the **AUTO-MEDIATOR** block (6 lines), then your verdict to the user — already cleaned up. If the cycle
sent you to get cheap evidence, get it and report with it. One pass, no rumination.

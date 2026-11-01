---
name: auto-mediator
description: Red-team your OWN verdict before you commit it — and resolve the doubt with evidence, not more thinking. Works for a single native model (Claude or any other) reasoning alone, or a multi-agent setup. Use before concluding ANY consequential yes/no, go/no-go, "can't / impossible / not supported / won't work", before rejecting a result, before abandoning an approach, OR before an irreversible / costly YES. Catches premature negatives ("no" that should be "yes" or "not yet"), over-eager positives, AND right-verdict-for-the-wrong-reason. Triggers on "red-team this", "devil's advocate", "steelman the opposite", "pre-mortem this", "pressure-test this", "is it really no?", and fires automatically whenever you are about to assert a consequential negative, a hard limit, or commit something irreversible.
---

# auto-mediator — mediate between your snap verdict and the evidence

Works whether you are **one native model reasoning alone** (Claude or any other) or orchestrating many.
The failure it fixes: closing too early — calling something impossible when it was "not yet", rejecting a
good result over a bad test, green-lighting a risky call on a hunch, or reaching a right answer by shallow
reasoning.

**Why it works the way it does.** Critiquing your own answer *without an external signal* usually makes it
worse — you flip correct answers to wrong and rarely see your real flaws (Huang et al., ICLR 2024).
Self-correction pays only with an **oracle**: running the test, calling another tool, measuring the number.
So this is **not "think harder" — it is "turn the doubt into a cheap EXTERNAL check."** Golden rule:
**flip a verdict on EVIDENCE, never on more reasoning.**

> **If you are a lone model with no council to consult, this matters MORE, not less.** You have no second
> training lineage to catch your blind spots, so external evidence and a genuine steelman are your *only*
> outside signal — don't substitute your own internal consensus for a check.

## When to fire
- Any **yes/no** that changes what you do, spends the user's resources, or closes off a path.
- **Always** before "can't / impossible / not supported / no way / won't work / reject".
- Before **abandoning** an approach, or an **irreversible / costly YES** (red-team the YES too).
- When the user says *red-team*, *devil's advocate*, *steelman it*, *pre-mortem*, *is it really no?*.
- NOT for reversible trivialities. **Don't ritualize it** — firing on everything dulls it. And keep it
  **scoped**: answer the specific decision, at the depth it needs; generic breadth around it is filler.

## The cycle (write it out, don't think it silently) — ONE pass
1. **Initial verdict + confidence** — but treat your own confidence as **suspect**: stated confidence is
   systematically overconfident ([Xiong 2023](https://arxiv.org/abs/2306.13063)). Low confidence is a trigger
   to get evidence; high confidence is **not** a reason to skip the check.
2. **Steelman the opposite** — the strongest real case for the other answer (not a straw man). Turn it into
   **2-3 verification questions** whose answer would **flip** the verdict; answer each with evidence.
3. **Not tried yet** — concrete tools / routes / approaches you have NOT attempted (see checklists).
4. **Bias** that may be pulling you there (see list).
5. **Cheap evidence that would change it** — what quick data / test / attempt confirms or flips this? If it's
   cheap, **GET IT BEFORE closing.** This is the core: resolve doubt with an oracle, not more text.
6. **Final verdict** — change it only if the evidence from step 5 warrants (not because you re-thought it).
   And check you are **right for the RIGHT REASON**: a correct verdict reached by generic or shallow
   reasoning is still a miss — name the **actual mechanism**, not the first plausible-sounding one.

## Premortem for a YES / GO (symmetry — don't only hunt the "no")
Before a costly / irreversible GO: **assume it already blew up 6 months from now — why?** List the plausible
causes (imagining the failure as already-happened raises your hit rate ~30%; Klein). Close any cause that's
cheap to close now (a mis-measured number, a short sample, an untested regime) before the GO.

## Checklist — "I concluded it's IMPOSSIBLE / blocked"
- Another **tool / method** not tried? (a different library, CLI, API, headless browser, public mirror).
- Another **endpoint / route / form** of the same resource? (an embed, a public API, a cache, an export).
- A different **permission / credential** path? (your own creds, ask the user to run it, approve the command).
- Blocked by a **filter / guardrail**, not true impossibility? → reframe safely, or escalate to the human.
- Can I **ask the user** for the missing piece instead of declaring it impossible?
- Is it "impossible" or "impossible **the way I tried it**"?

## Checklist — "I'm REJECTING a result / test / analysis as a failure"
- **Units / inputs correct?** A wrong unit, scale, or a placeholder instead of the real measured value is a
  classic **silent 10× error** that sinks a good result. Verify the number before you trust it.
- **Does my implementation match the method being tested?** A failure of the *naive* version doesn't refute
  the *refined* one → often the right verdict is **"not evaluated yet"**, not "doesn't work".
- **Realistic costs / overhead included?** Does the effect exist *before* costs?
- **Any leakage / look-ahead** that would flip the sign?
- **Enough sample and regime diversity?** (a short window = provisional).
- **Direction of the test's bias:** a SOLID negative (failed even the lenient version) or a FRAGILE one?

## Biases to name out loud
premature closure · confirmation (seeking data that backs my first "no") · anchoring to the first failed
attempt · giving up after 1-2 guardrail blocks · cost/overfitting/sample traps when judging a result ·
assuming the source's claim is false (or true) without measuring · **overconfidence in my own judgment and in
my stated confidence** · mistaking the right verdict for right reasoning.

## More is not the lever
More deliberation, more self-talk, a longer chain — these plateau or backfire ([self-consistency and long
CoT can hurt](https://arxiv.org/pdf/2503.22732)). The levers are **external grounding, scope, and (when
available) a different lineage** — not volume. One pass; resolve with evidence; escalate only if the fork is big.

## Escalate to a multi-agent council (optional, for big forks)
If the fork is **big** (real money, production, irreversible) and you *can* reach other models, escalate to a
**council**: several **different-lineage** models analyze, peer-review anonymously, and a chair synthesizes
— cross-model diversity (not more clones) is what adds coverage ([Du 2023](https://arxiv.org/abs/2305.14325)).
A provider-agnostic reference lives in [`council/`](council/). No council available? Fall back to the lone-model
rule above: lean harder on external evidence.

## Close the loop (so you don't trip the same way twice)
If the cycle **flipped** a verdict, record the lesson. But the checklists are **memory, not the fix** — don't
let them grow into an n+1 pile of per-bias patches. The durable improvements are the **transversal** ones
(external evidence, scope, mechanism-focus, calibration), which correct *any* bias at once.

## Output
First the **AUTO-MEDIATOR** block, then your verdict to the user — already cleaned up. If the cycle sent you to
get cheap evidence, get it and report with it. One pass, no rumination.

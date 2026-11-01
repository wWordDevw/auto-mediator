# Parameters over patches — improving agent reasoning horizontally, and measuring it

## The thesis

Fixing an agent's reasoning by adding one rule per observed bias ("premature closure → add a checklist
item"; "wrong units → add a units check") is **n+1 growth**: linear, vertical, and it never generalizes
to the bias you haven't seen yet. The checklist gets longer; the agent doesn't get *structurally* better.

The alternative is **horizontal**: find the small set of **transversal parameters** that move reasoning
quality across *all* bias types at once, and **measure** their effect on a held-out distribution rather
than on the anecdote that motivated them. A patch improves one case. A parameter improves the distribution.

## Honest evaluation of this very project (auto-mediator)

Run auto-mediator through its own lens:

- **~70% patch (n+1):** the two checklists ("impossible/blocked", "rejecting a result") are a growing list
  of specific past failures. Useful as memory, but they are exactly the n+1 pattern — they don't cover the
  next unseen bias.
- **~30% transversal (the good part):**
  - **The oracle rule** ("resolve doubt with external evidence, not more reasoning") is a *horizontal* lever:
    it corrects *any* bias, because the fix is external verification, not enumerating the bias. This is the
    one genuinely structural idea in the skill.
  - **Premise-challenge / steelman** applies to any verdict.
  - **Cross-lineage council** is a transversal lever (see below).
- **0% measured.** Every claim of improvement here ("flipped a false NO-GO", "diversity caught the premise")
  is an **anecdote**. Nothing was evaluated on a held-out set. By the project's own standard — *evidence, not
  reasoning* — our evidence for the skill working is weak.

**Diagnosis:** auto-mediator is a patch-pile with two or three real levers and no measurement. The upgrade is
**not more checklist items**. It is (1) lean on the transversal levers, and (2) build the measurement system
so every future change is judged on a distribution, not a story.

## The transversal parameters (the actual levers), each measurable

| Parameter | What it is | What the evidence says | Caveat |
|---|---|---|---|
| **External-evidence ratio** | how often doubt triggers an oracle check (test, tool, lookup) vs self-talk | self-correction *without* an external signal degrades reasoning; external feedback is what helps ([Huang 2024](https://arxiv.org/abs/2310.01798)) | needs an available oracle; useless for pure-judgment calls |
| **Inference / reasoning budget** | samples (self-consistency), search, thinking tokens | compute-optimal allocation can beat scaling model size; 4× test-time ≈ 4× bigger model on hard items ([Snell 2024](https://arxiv.org/pdf/2503.22732)) | **non-monotonic** — longer chains and naive self-consistency can *hurt*; best strategy depends on budget/difficulty |
| **Ensemble heterogeneity** | members from different *lineages*, chosen for complementary errors | cross-**model** diversity beats prompt diversity; homogeneous agents show **strong diminishing returns** ([complementary-agents, NeurIPS 2025](https://arxiv.org/abs/2605.24048)) | diversity ≠ gain; what matters is **complementarity**, not count (more clones is itself n+1) |
| **Scope / framing** | bounding the ask; explicit premise-challenge | an agent reasons only within the frame given; unscoped prompts return generic breadth | over-narrow scope hides relevant angles |
| **Calibration** | does stated confidence track accuracy | verbalized confidence is **systematically overconfident** and saturates high; RLHF worsens it ([Xiong 2023](https://arxiv.org/pdf/2306.13063), [Leng 2024](https://arxiv.org/html/2410.09724v1)) | our skill's "confidence %" is itself unreliable until measured (ECE/Brier) |

Note the pattern: **"more" is not the lever.** More agents, more tokens, more checklist — all hit diminishing
returns or can backfire. The lever is *complementarity, compute-optimal allocation, and external grounding*,
found by measurement — not cranked up by assumption.

## The missing piece: a measurement system (without it, "transversal" and "measurable" are just words)

Recent harness-aware evaluation work makes the case directly:

- A benchmark score is the **model + harness pairing**, not the model alone; **choosing the best harness can
  yield gains comparable to choosing the best LLM** ([harness survey](https://arxiv.org/pdf/2606.20683),
  [ICML 2026](https://icml.cc/virtual/2026/68323)). So our parameters (the harness) are worth as much as the
  base model — and their effect **can be statistically attributed**.
- But methods that **tune on the same benchmark they report on overfit** and inflate gains
  ([harness-evolution critique](https://www.opentrain.ai/papers/rethinking-the-evaluation-of-harness-evolution-for-agents--arxiv-2607.12227/)).
  → evaluate on **held-out** cases, with **oracle-checkable** scoring and consistent budgets.

**Concrete next step (the real work):** build a small **held-out eval suite** — decision/reasoning cases with
*known* answers, spanning the bias types we care about (premature "impossible", mis-measured inputs, premise
traps, over-eager GO). Score oracle-checkably. Then measure each parameter's effect **across the suite**, and
attribute the gain to the parameter vs the base model. Only then is a change "transversal and measurable" —
instead of a patch justified by the one case that inspired it.

**Metrics to track:** suite accuracy (oracle-checkable), premise-trap catch rate, false-negative-flip rate,
calibration (ECE/Brier), and cost — so we optimize for the *compute-optimal* point, not the maximum.

## In one line

Stop patching biases one by one (n+1). Pick the few transversal levers — external grounding, complementary
ensembles, compute-optimal budget, scope, calibration — and build a held-out eval suite so every change is
measured on the distribution, not sold with an anecdote.

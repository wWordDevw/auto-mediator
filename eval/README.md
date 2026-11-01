# eval — a held-out suite to measure reasoning quality (v0)

The measurement system that `docs/PARAMETERS_OVER_PATCHES.md` argues for: instead of judging a change
by the one anecdote that inspired it, measure it on a **held-out distribution** of cases with **known
answers**, scored by an **oracle** (a parseable verdict), not by an LLM judging vibes.

## What it measures

Each case in [`cases.jsonl`](cases.jsonl) is a decision with a known correct verdict, across bias types:

| category | the trap | correct answer is… |
|---|---|---|
| `premature-impossible` | calling something impossible too early | the positive ("it's possible") |
| `premise-trap` | a flawed premise stated as fact | reject it ("flawed") |
| `unit-input-error` | a wrong unit/scale that flips a conclusion | distrust the number ("suspect") |
| `over-eager-go` | green-lighting on unrepresentative evidence | hold |
| `solid-negative` | a genuine hard limit | the negative ("impossible") |

The suite is **balanced on direction**: some cases are only right if you *stop over-rejecting*
(`premature-impossible`), others only right if you *correctly reject* (`solid-negative`). So you can't
score well by always flipping to "yes" or always to "no" — it rewards calibrated judgment, not a reflex.

## Run

```bash
export OPENAI_API_KEY=...
python eval/run_eval.py --model gpt-4o-mini                      # baseline
python eval/run_eval.py --model gpt-4o                           # parameter: stronger model
python eval/run_eval.py --model gpt-4o-mini --samples 5 --temperature 0.7   # parameter: inference budget (self-consistency)
```

It prints per-case pass/fail, accuracy overall and per category, a **right-for-the-right-reason** rate
(did it reach the verdict via the correct reason, not luck), a **calibration** readout (Brier + mean
confidence on correct vs wrong — a tiny or negative gap means overconfidence), and the call cost.

## How to read it

The point isn't the absolute score — it's **comparing parameter settings on the same held-out suite**.
Run two models, or N vs 1 samples, and see which moves accuracy / calibration / right-reason *across the
distribution*. That is a transversal, measured change — the opposite of an n+1 patch.

## Honest limits (it's a v0 skeleton)

- **10 cases is not a benchmark.** It's a seed. Grow it (aim for dozens per category) and keep a
  held-out split you never tune on — tuning prompts on these exact cases and then reporting on them
  overfits (the failure mode in the harness-evolution literature).
- **The verdict oracle is robust; the reason check is keyword-based** (approximate — a model can hit the
  keyword without truly reasoning, or reason correctly in other words). Treat `right-for-right-reason`
  as indicative, not exact. A later version can add an LLM-judge with an explicit rubric, or
  executable/state checks, for harder cases.
- **Confidence** is self-reported and known to be overconfident; the calibration readout measures exactly
  that, it doesn't fix it.

## Next (v1)

- More cases per category; a frozen held-out split.
- A `--council <config.json>` solver to measure the ensemble-heterogeneity parameter here too.
- A rubric-based judge for cases whose answer isn't a clean token.

# eval — a held-out suite to measure reasoning quality (v1)

The measurement system that `docs/PARAMETERS_OVER_PATCHES.md` argues for: instead of judging a change
by the one anecdote that inspired it, measure it on a **held-out distribution** of cases with **known
answers**, scored by an **oracle** (a parseable verdict), not by an LLM judging vibes.

## What it measures

20 cases in [`cases.jsonl`](cases.jsonl), 4 per bias type, each with a known correct verdict:

| category | the trap | correct answer is… |
|---|---|---|
| `premature-impossible` | calling something impossible too early | the positive ("it's possible") |
| `premise-trap` | a flawed premise stated as fact | reject it ("flawed") |
| `unit-input-error` | a wrong unit/scale that flips a conclusion | distrust the number ("suspect") |
| `over-eager-go` | green-lighting on unrepresentative evidence | hold |
| `solid-negative` | a genuine hard limit | the negative ("impossible") |

The suite is **balanced on direction**: some cases are right only if you *stop over-rejecting*
(`premature-impossible`), others only if you *correctly reject* (`solid-negative`). You can't score well by
always flipping to "yes" or always to "no" — it rewards calibrated judgment, not a reflex.

## Run — compare parameter settings on the same suite

```bash
export OPENAI_API_KEY=...   # (+ GEMINI_API_KEY, DEEPSEEK_API_KEY for the council)

python eval/run_eval.py --model gpt-4o-mini                       # baseline model
python eval/run_eval.py --model gpt-4o                            # parameter: stronger model
python eval/run_eval.py --model gpt-4o-mini --samples 5 --temperature 0.7   # parameter: inference budget
python eval/run_eval.py --council council/config.json             # parameter: cross-lineage ensemble
python eval/run_eval.py --council council/config.json --ids cuda-cpu,machine-code   # a subset (the council is slow)
```

It prints per-case pass/fail, accuracy overall and per category, a **right-for-the-right-reason** rate (did
it reach the verdict via the correct reason, not luck), **calibration** (Brier + mean confidence on correct
vs wrong — a small/negative gap means overconfidence), and the call cost.

## What the numbers already show (why this beats anecdotes)

Measured on this suite, varying one parameter at a time:

- **Stronger model** (gpt-4o vs gpt-4o-mini): same verdict accuracy, but right-for-right-reason 50%→60% — it
  reaches correct conclusions via correct reasoning more often.
- **Harder cases de-saturate the oracle:** gpt-4o-mini scores 19/20, and its one miss (`cuda-cpu`) comes with
  *higher* confidence than its average correct answer — overconfidence on the error, now visible.
- **Cross-lineage council** (`--council`): fixed the single-model miss (`cuda-cpu`) and scored 8/8 on a mixed
  subset. Different training lineages cover each other's blind spots — the parameter paying off, on the suite.

## Honest limits

- **20 cases is a seed, not a benchmark.** Grow it (dozens per category) and keep a held-out split you never
  tune on — tuning prompts on these exact cases and reporting on them overfits.
- **The verdict oracle is robust; the reason check is keyword-based** (approximate). Treat
  `right-for-right-reason` as indicative. A rubric-based judge would harden it for cases without a clean token.
- **Confidence** is self-reported and known to be overconfident; the calibration readout measures that, it
  doesn't fix it.
- **The council solver is slow and expensive** (~N·2+1 calls per case) and will skip any model that is down or
  rate-limited (it proceeds on the rest). It's the high-stakes escalation, not the default — run it on subsets.

## Next

- A frozen held-out split; more cases per category.
- A rubric-based judge for cases whose answer isn't a clean token.
- Parallelize the council's per-stage calls so the full suite runs in reasonable time.

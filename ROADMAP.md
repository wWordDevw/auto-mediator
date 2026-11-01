# Roadmap — next features

Recorded, not built yet.

## Selectable effort / debate depth (planned)

Let the caller pick **how hard to debate something, matched to the stakes** — a dial from a quick single-pass
check to a deep multi-round council. The idea:

- a **low-effort** mode — one model, one pass, minimal tokens — for low-stakes or easily reversible calls;
- a **high-effort** mode — cross-lineage council, more rounds, larger inference budget — for big or
  irreversible forks;
- the level chosen explicitly by the caller, or inferred from the stakes of the decision.

This maps *effort* (inference budget + ensemble size + rounds) to *how much a decision is worth debating*, so
we don't pay full council cost on trivia or under-debate a costly fork. It turns the transversal parameters
(inference budget, ensemble heterogeneity) into a single stakes-aware knob.

## Other planned

- **Parallelize** the council's per-stage calls so the full 20-case eval suite runs in reasonable time.
- A **frozen held-out split** for the eval suite; more cases per category.
- A **rubric-based judge** for eval cases whose answer isn't a clean token.

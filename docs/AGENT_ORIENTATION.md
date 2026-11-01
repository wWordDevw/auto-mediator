# Orienting an agent — five rules

Distilled from live council tests (running the same decision through 2-model same-provider
councils vs cross-provider councils, and watching where reasoning got sharper or stayed generic).
These are about *how you aim and bound* an agent, not about any single prompt.

### 1. Diverse lineage beats more of the same
Two models from the same family tend to think alike — they agree, and the agreement is shallow.
Adding a model from a **different training lineage** (a different provider) brought in an angle the
same-family council missed entirely. For coverage and blind spots, use genuinely different models,
not N copies of one. An agent "reaching consensus with itself" is a false consensus.

### 2. An agent reasons *within* the frame you give it
Neither council spontaneously challenged a flawed premise in the question — they answered the
question as framed. If the right answer depends on **questioning the premise**, instruct that
explicitly ("first, does the premise hold?"). Don't expect framing to be challenged for free.

### 3. Scoping the prompt bounds the reasoning
Left open, the council spent effort on generic points the asker already knew and under-weighted the
novel, decision-specific angle. **The scope of the prompt is the limit of the reasoning.** If you need
one specific kind of analysis, constrain the ask to it; breadth without scope is filler.

### 4. Models are opinion engines, not evidence
Both councils ended with "an empirical study would settle it" — an honest admission that the verdict
was opinion. For questions with a **knowable** answer (technical, factual), orient the agent to **fetch
evidence** (benchmarks, docs, a quick test), not to deliberate. Reserve deliberation for genuine
judgment calls where no evidence is available.

### 5. The disagreement is the product, not the verdict
The most useful output of a council is **where it splits and what evidence would resolve the split** —
not the yes/no. Orient agents to surface the disagreement and the deciding evidence, rather than forcing
one confident answer.

---

**In one line:** diverse lineage adds coverage; prompt scope sets the reasoning boundary; and for the
knowable, evidence beats deliberation. Encode this in *how you launch and bound* agents.

> These five are heuristics for *aiming* an agent. They do not fix an agent's structural reasoning
> biases — that needs transversal, measured parameters, not per-bias patches. See the companion analysis.

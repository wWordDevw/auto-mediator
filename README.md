# auto-mediator

**Red-team your own verdict before you commit it — and resolve the doubt with evidence, not more thinking.**

An agent skill that makes an AI (or a person) stop closing too early: declaring something *impossible*
when it was *not yet*, rejecting a good result over a bad test, or green-lighting a risky call on a hunch.

## Why not just "ask the model to critique itself"?

Because that backfires. Research shows that **intrinsic self-correction — a model revising its own answer
with no external signal — usually makes things worse**: it flips correct answers to wrong ones and rarely
spots its real flaws ([Huang et al., *LLMs Cannot Self-Correct Reasoning Yet*, ICLR 2024](https://arxiv.org/abs/2310.01798)).
Self-correction only pays when there is an **oracle** — running the test, calling another tool, measuring
the real number.

**auto-mediator is built around that oracle.** It treats your own judgment as unreliable and turns every
doubt into a *cheap external check*. The golden rule is simple: **flip a verdict on evidence, never on more
reasoning.**

## How it compares

| Technique | What it does | Gap auto-mediator closes |
|---|---|---|
| Self-Refine | generate → critique → revise, same model, no external signal | adds the **oracle rule** (resolve doubt with evidence, not self-talk) |
| Chain-of-Verification | generate verification questions, answer them | keeps it, and ties each question to a verdict-flip |
| Reflexion | store critiques in memory across attempts | adds **"close the loop"** (record the lesson into the checklists) |
| Multi-agent debate | several agents debate | included as an **optional escalation** ([`council/`](council/)) for big forks |
| Pre-mortem | "assume it failed, why?" | included, but **symmetric** — applied to over-eager *yes* as well as *no* |

Most self-critique prompts are **symmetric and vague**, and lean on the model talking to itself.
auto-mediator is **asymmetric by design** (it hunts the premature *no* first, where the costliest misses hide),
**evidence-first** (doubt becomes an action, not a paragraph), and ships **domain checklists** you extend.

## Install

**Claude Code:** copy the skill into your skills directory —

```bash
git clone https://github.com/wWordDevw/auto-mediator.git
mkdir -p ~/.claude/skills/auto-mediator
cp auto-mediator/SKILL.md ~/.claude/skills/auto-mediator/SKILL.md
```

**Any other agent / harness:** the skill is a single self-contained `SKILL.md`. Load its body as a system
or developer instruction, or paste it into your prompt. It depends on nothing proprietary.

## Use

It fires automatically before a consequential verdict, or on demand:

> *"red-team this"*, *"devil's advocate"*, *"steelman the opposite"*, *"pre-mortem this"*, *"is it really no?"*

The agent then writes a short **AUTO-MEDIATOR** block (verdict + confidence → steelman with verification
questions → what's untried → bias → **cheap evidence to go get** → final verdict), and only flips its answer
if the evidence warrants. See [`examples/`](examples/) for worked runs.

## Optional: the multi-agent council

For high-stakes forks (real money, production, irreversible calls), one agent debating itself isn't enough.
[`council/`](council/) ships a provider-agnostic reference that runs several independent models, has them
peer-review each other's answers anonymously, and synthesizes a final verdict — the pattern that beats a
single model on reasoning and factuality ([Du et al., 2023](https://arxiv.org/abs/2305.14325)).

## References

- Huang et al., *Large Language Models Cannot Self-Correct Reasoning Yet*, ICLR 2024 — [arXiv:2310.01798](https://arxiv.org/abs/2310.01798)
- Du et al., *Improving Factuality and Reasoning in Language Models through Multiagent Debate*, ICML 2023 — [arXiv:2305.14325](https://arxiv.org/abs/2305.14325)
- Madaan et al., *Self-Refine: Iterative Refinement with Self-Feedback*, 2023 — [arXiv:2303.17651](https://arxiv.org/abs/2303.17651)
- Dhuliawala et al., *Chain-of-Verification Reduces Hallucination*, 2023 — [arXiv:2309.11495](https://arxiv.org/abs/2309.11495)
- Gary Klein, *Performing a Project Premortem*, HBR 2007 — [pre-mortem](https://en.wikipedia.org/wiki/Pre-mortem)

## License

MIT — see [LICENSE](LICENSE).

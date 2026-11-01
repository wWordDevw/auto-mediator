# The multi-agent council (optional escalation)

When a decision is big enough that one agent debating itself isn't enough — real money, shipping to
production, an irreversible call — escalate from the single-agent `auto-mediator` cycle to a **council**:
several independent agents analyze the question, peer-review each other anonymously, and a chair synthesizes
a final verdict. Multiple agents debating beat a single model on reasoning and factuality
([Du et al., 2023](https://arxiv.org/abs/2305.14325)); anonymous peer review reduces deference and groupthink.

## The protocol (3 stages)

1. **Independent analysis.** Each model answers the question *on its own*, with no sight of the others.
   This preserves genuine diversity of reasoning (the whole point — correlated answers add nothing).
2. **Anonymous peer review.** Each model sees all answers, stripped of authorship and shuffled
   (`Response A/B/C…`), and critiques + ranks them. Anonymity stops "it's the big model, defer to it".
3. **Synthesis.** A chair model reads the answers *and* the reviews and writes the final verdict, noting
   where the council agreed, where it split, and what evidence would settle the split.

The output is not a vote — it's a synthesis that **surfaces the disagreement** so you decide with eyes open.

## Reference implementation

[`council.py`](council.py) is a zero-dependency (Python 3 stdlib only) runner for any
**OpenAI-compatible** chat API. Point it at whichever models you have:

```bash
cp council/config.example.json council/config.json   # edit: your models + API base URLs
export OPENAI_API_KEY=...        # and any other keys your config references
python council/council.py "Should we ship the new pricing page this week?"
```

Each model entry names the env var that holds its key, so you can mix providers (OpenAI, a local
server, an OpenAI-compatible gateway, etc.). Diversity of *providers* beats several calls to one model.

It is a **reference template**, deliberately small and readable — adapt it, don't treat it as a framework.

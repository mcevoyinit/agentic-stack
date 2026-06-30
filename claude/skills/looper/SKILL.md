---
name: looper
description: |
  Run all three self-deliberation loops (Gemini, GPT, Grok) in parallel. Each model argues with
  itself independently through 3-4 rounds (Analyst → Adversary → Integrator → Decider). No chairman,
  no cross-model synthesis — just three independent battle-tested analyses side by side.
  Lighter than /council or /kamikaze. Use when you want depth from multiple models without the
  overhead of structured council deliberation.
  Trigger: "looper", "all loops", "triple loop", "run all loops", "loop all models".
version: 1.0.0
---

# Looper — Parallel Self-Deliberation Loops

## What This Is

Fires all three model-specific loops in parallel:

| Loop | Model | Script |
|------|-------|--------|
| Gemini Loop | gemini-3.5-flash | `~/.claude/skills/gemini-loop/utils/gemini_loop.py` |
| OpenAI Loop | gpt-5.5 | `~/.claude/skills/openai-loop/utils/openai_loop.py` |
| Grok Loop | grok-4.3 | `~/.claude/skills/grok-loop/utils/grok_loop.py` |

Each loop runs 3-4 rounds independently (Analyst → Adversary → Integrator → Decider).
No chairman. No synthesis across models. Just three independently stressed analyses.

### How it differs from Council/Kamikaze

| Feature | Looper | Council/Kamikaze |
|---------|--------|------------------|
| Cross-model synthesis | No | Yes (chairman) |
| Adversarial rounds | Self only | Between models |
| Chairman/synthesis agent | None | Claude Opus |
| Depth per model | 3-4 rounds | 1-2 rounds |
| Overhead | Low | High |
| Best for | Deep independent insight | Consensus/decision |

## When to Use

**Use Looper when**:
- You want three deep, independent analyses without mediator overhead
- Each model should argue with itself, not with each other
- You want to compare how different models reason through the same problem
- Depth matters more than consensus

**Use `/council` or `/kamikaze` instead when**:
- You need a synthesized answer across models
- Cross-model adversarial debate matters
- You want a chairman to resolve disagreements

**Use a single loop (`/gemini-loop`, `/openai-loop`, `/grok-loop`) when**:
- One model's perspective is enough
- You want to save cost/time
- You trust one model more for this particular domain

## How to Activate

When the user invokes this skill, collect:
1. **Topic** — What question to analyze (required)
2. **Context** — Background info, constraints, existing work (optional)
3. **Rounds** — 3 (default) or 4 (adds final Decision round)
4. **Models** — Which loops to run: `all` (default), or comma-separated: `gemini,openai,grok`
5. **Output dir** — Where to save results (optional, suggest `docs/analysis`)

Then run:
```bash
python3 ~/.claude/skills/looper/utils/looper.py \
  --topic "Your question here" \
  --context "Background information" \
  --rounds 3 \
  --output-dir docs/analysis
```

### Selective models:
```bash
python3 ~/.claude/skills/looper/utils/looper.py \
  --topic "..." \
  --models gemini,grok \
  --rounds 4
```

### With a context file:
```bash
python3 ~/.claude/skills/looper/utils/looper.py \
  --topic "Analyze this architecture" \
  --context-file docs/architecture.md \
  --rounds 4
```

## Cost & Time Estimates

All three run in parallel, so wall-clock time ≈ slowest loop, not sum.

| Config | Wall-Clock Time | Total API Cost (est.) |
|--------|----------------|----------------------|
| 3 rounds, all models, short | ~5-8 min | ~$0.60-1.70 |
| 3 rounds, all models, large context | ~8-12 min | ~$1.70-4.30 |
| 4 rounds, all models, large context | ~10-15 min | ~$3.00-7.20 |
| 2 models only | ~70% of above | ~65% of above |

## After Running

Present the results with:
1. **Per-model final synthesis** (R3 or R4 from each loop)
2. **Where models agree** — high-confidence shared conclusions
3. **Where models diverge** — interesting disagreements worth noting
4. Note: Do NOT synthesize into a single answer — that's council territory. Let the user decide.

## Security Notes

**NEVER send**:
- API keys, tokens, credentials
- Customer PII or private data
- Internal server names / IPs

**Safe to send**:
- Architecture descriptions
- Strategic questions
- Sanitized code snippets
- Business model analysis

---
name: kamikaze
description: Run recursive multi-AI strategic deliberation with adaptive depth (2-6 rounds). V4 introduces thermodynamic architecture with CAS backbone, Crux Ledger handoffs, multi-signal convergence, unified adversary engine, and Decision Snapshot outputs. Uses GPT-5.5+Gemini 3.5+Grok 4.3. 11 goal-specific templates with auto-suggest. Use for major strategic decisions, roadmap planning, or when you need maximum insight.
---

# Kamikaze Council Skill

## Ultimate Kamikaze V4 (Recommended)

**NEW in V4**: Thermodynamic architecture with immutable CAS storage, structured Crux Ledger handoffs, multi-signal convergence detection, unified adversary engine with personas, and rich Decision Snapshot outputs with minority opinion preservation.

| Version | Cost | Time | Use Case |
|---------|------|------|----------|
| **V4 (Thermodynamic)** | $3-5 | ~8-15 min | Default - CAS backbone, Crux Ledger, multi-signal convergence |
| V3 (Ultimate) | $0.75-2 | ~5-10 min | Lightweight - adaptive depth, structured handoffs |
| V2 (Debate) | $1-3 | ~8-12 min | Basic debate mode, no structured handoffs |
| V1 (Legacy) | $5-15 | ~15-20 min | Maximum depth, full 5 rounds always |

```bash
# V4 with auto-suggest template (default)
python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v4.py \
  --topic "Is this worth pursuing?"

# V4 with explicit template
python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v4.py \
  --topic "What's our 90-day roadmap?" --template 90-day-plan

# V4 with adversarial deep-dive
python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v4.py \
  --topic "Critical architecture decision?" --template deep-technical

# V4 exhaustive mode (max rounds, no early stop)
python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v4.py \
  --topic "Major strategic decision?" --depth exhaustive
```

---

## V4 Key Innovations

### 1. CAS Backbone (Content-Addressable Storage)
- **Immutable**: Every artifact (synthesis, crux, ledger) is content-addressed via SHA-256
- **Provenance**: Full lineage tracking - trace any insight back to source
- **Deduplication**: Same content = same hash = stored once
- **"Open Writes, Typed Reads"**: Accept all data, filter on retrieval

### 2. Crux Ledger (Structured Handoffs)
- **Stable IDs**: `C-YYYY-MM-DD-NNN` format for cross-round references
- **Verbatim Snippets**: Pro/con quotes (≤40 words) embedded in ledger
- **Minority Scores**: 0-1 score showing model disagreement level
- **Flip Conditions**: "Flips if X?" - what would change the conclusion
- **Entailment Scores**: NLI-derived confidence for pro/con arguments

### 3. Multi-Signal Convergence Engine
- **Geometry**: Position radius and velocity in semantic space
- **Entropy**: Compression ratio and n-gram overlap detection
- **Novelty**: MinHash similarity and residual claim count
- **Disagreement**: Minority score preservation threshold

### 4. Unified Adversary Engine
Personas available for adversarial rounds:
- **Ruthless Logician**: Pure logical attack on reasoning
- **Red Team**: Security/failure mode thinking
- **Contrarian**: Deliberate opposite position
- **Hostile Debater**: Aggressive challenge mode
- **Devil's Advocate**: Steelman opposition

### 5. Decision Snapshots (Rich Output)
- **Above-the-Fold**: 3-sentence executive summary
- **Minority Panel**: Preserved dissenting opinions with strength scores
- **Conditional Actions**: "Do X if Y" / "Do X unless Z" format
- **Fragility Markers**: Evidence sensitivity indicators
- **Crux References**: Link actions back to supporting cruxes

---

## 11 Goal-Specific Templates

| Template | Rounds | Best For |
|----------|--------|----------|
| **strategy** | Analysis→Challenge→Prioritize→Risk→Action | Business/product strategy |
| **technical** | Analysis→Challenge→Prioritize→Risk→Action | Technical architecture |
| **product** | Analysis→Challenge→Prioritize→Risk→Action | Product planning |
| **postmortem** | Analysis→Challenge→Synthesize→Risk→Action | Incident review |
| **viability** | Analysis→Challenge→Synthesize→Decide | Go/no-go decisions |
| **90-day-plan** | Analysis→Prioritize→Sequence→Risk→Action | Quarterly roadmaps |
| **pure-insight** | Analysis→Challenge→Challenge→Synthesize | Deep understanding (no actions) |
| **monetization** | Analysis→Challenge→Prioritize→Risk→Action | Business model & pricing |
| **technical-direction** | Analysis→Challenge→Sequence→Risk→Synthesize→Action | Multi-year architecture |
| **adversarial-strategy** | Analysis→Challenge→**Adversary**→Prioritize→Risk→Action | Strategy with red team |
| **deep-technical** | Analysis→Challenge→**Adversary**→Synthesize→Risk→Action | Technical with adversarial review |

---

## Depth Options

| Depth | Rounds | Early Stop | Adversary | Use Case |
|-------|--------|------------|-----------|----------|
| **quick** | 2-3 | Yes | No | Fast answers |
| **standard** | 3-4 | Yes | Yes | Default balanced |
| **thorough** | 4-5 | Yes | Yes | Important decisions |
| **legacy** | 5 | No | Yes | Full depth (V3 compat) |
| **exhaustive** | 5-6 | No | Yes | Maximum insight |

---

## Template Selection Guide

```
START: What question are we answering?

├─ "Is this worth doing?" / "Should we invest?"
│  └─ viability (4R, stops at decision)
│
├─ "Help me understand..." / "Why does..."
│  └─ pure-insight (4R, no action plan)
│
├─ "What's our quarterly roadmap?"
│  └─ 90-day-plan (5R, weekly granularity)
│
├─ "How should we architect this?"
│  ├─ Short-term? → technical (3-5R)
│  ├─ Multi-year? → technical-direction (6R)
│  └─ Need red team? → deep-technical (6R with adversary)
│
├─ "What's the worst that could happen?"
│  └─ adversarial-strategy (6R with red team)
│
├─ "How should we price/monetize?"
│  └─ monetization (5R)
│
├─ "What went wrong?"
│  └─ postmortem (5R)
│
└─ "What's our strategy?"
   └─ strategy (3-5R, default)
```

---

## Activation Triggers

**ACTIVATE** when user:
- Mentions "kamikaze", "battleception", "strategic analysis"
- Wants "deep strategic analysis", "full deliberation", "recursive council"
- Asks for "roadmap planning", "90-day plan", "strategic priorities"
- Needs "viability analysis", "go/no-go decision"
- Wants "maximum insight" or "comprehensive analysis"
- Needs "red team", "adversarial analysis", "worst case"

**DO NOT activate** for:
- Simple questions (use a single `/gemini`, `/openai`, or `/grok` call instead)
- Single-round council needs
- When user explicitly wants quick answers

---

## CLI Options

### V4 (Recommended)
```bash
python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v4.py \
  --topic "Your strategic question" \    # Required
  --context "Background info" \          # Optional context
  --template auto \                      # auto, strategy, viability, etc.
  --depth standard \                     # quick, standard, thorough, legacy, exhaustive
  --adversary red_team \                 # Optional: force specific adversary persona
  --output-dir docs/kamikaze             # Output location
```

### V3 (Lightweight)
```bash
python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v2.py \
  --topic "Your strategic question" \
  --template auto \
  --depth standard \
  --mode v3 \
  --output-dir docs/kamikaze
```

---

## Important Rules

### DO:
- Use V4 for important decisions (richer outputs, minority preservation)
- Use V3 for quick iterations (cheaper, faster)
- Let auto-suggest pick template when unsure
- Trust early stopping (based on multi-signal convergence)
- Use `--depth exhaustive` for audit trails
- Read the Decision Snapshot minority panel!
- Save outputs to `docs/kamikaze/` for reference

### DON'T:
- Run Kamikaze for simple questions (a single `/gemini`/`/openai`/`/grok` call is enough)
- Override early stopping without specific reason
- Skip reading the minority opinions
- Ignore flip conditions - they reveal fragility!
- Use V4 if cost is primary concern (use V3)

---

## V4 Output Files

```
docs/kamikaze/kamikaze_v4_YYYYMMDD_HHMMSS/
├── KAMIKAZE_FINAL_REPORT.md      # Decision Snapshot (main output)
├── DECISION_SNAPSHOT.json        # Structured snapshot data
├── CAS_PROVENANCE.json           # Full artifact lineage
├── ROUND_1_SYNTHESIS.md          # Round 1 output
├── ROUND_1_CRUX_LEDGER.json      # Round 1 cruxes
├── ROUND_1_DEBUG.json            # Round 1 metrics
├── ROUND_2_SYNTHESIS.md
├── ROUND_2_CRUX_LEDGER.json
├── ROUND_2_DEBUG.json
└── ...
```

---

## Security Notes

**NEVER include**:
- API keys, passwords, tokens
- Customer PII
- Confidential financial data
- Proprietary algorithms without sanitization

**Safe to include**:
- Public documentation
- Anonymized business metrics
- General architecture descriptions
- Strategic questions

---

## Example Invocations

**V4 Viability Analysis**:
```bash
python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v4.py \
  --topic "Should we invest in building our own auth system vs using Auth0?" \
  --context "Currently using Auth0 at $500/mo, considering in-house for control"
```

**V4 Adversarial Strategy**:
```bash
python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v4.py \
  --topic "What are the fatal flaws in our expansion plan?" \
  --template adversarial-strategy \
  --depth exhaustive
```

**V4 90-Day Roadmap**:
```bash
python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v4.py \
  --topic "What should our Q1 2026 engineering priorities be?" \
  --context "3 engineers, $50K budget, launching mobile app" \
  --template 90-day-plan
```

**V4 Deep Technical**:
```bash
python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v4.py \
  --topic "Should we migrate from monolith to microservices?" \
  --template deep-technical \
  --depth thorough
```

**V3 Quick Analysis** (cost-sensitive):
```bash
python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v2.py \
  --topic "Quick viability check on feature X" \
  --depth quick
```

---

## Slash Command

```bash
/kamikaze What should our strategic priorities be for 2026?
```

This activates the skill with V4, auto-suggest template, and standard depth.

---

## Version History

- **V4 (2026-01)**: Thermodynamic architecture - CAS backbone, Crux Ledger, multi-signal convergence, unified adversary, Decision Snapshots
- **V3 (2025-10)**: Ultimate Evolution - structured handoffs, adaptive depth, auto-suggest, 9 templates
- **V2 (2025-08)**: Debate mode - 2-model debate + judge, convergence detection
- **V1 (2025-06)**: Original - 3-model parallel, 5 fixed rounds

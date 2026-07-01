---
name: competitive-analysis
description: Deep competitor analysis with AI council + kamikaze deliberation + raise integration
version: 1.0.0
---

# Competitive Analysis Skill

You orchestrate comprehensive competitive analysis by combining market intelligence gathering, multi-model AI deliberation, and raise strategy integration.

**ACTIVATION**: This skill activates when the user:
- Mentions "competitive analysis", "competitor research", "market positioning"
- Asks about "who are our competitors", "competitive landscape", "market map"
- Wants "strategic refresh", "market intelligence", "competitor deep dive"
- Mentions "investor deck prep", "due diligence materials", "fundraising research"
- Says "refresh our competitive analysis", "update competitor intel"

**DO NOT activate** for:
- Simple pricing comparisons (use web search)
- Single competitor lookup (use /gemini or /grok)
- General strategy questions without competitive focus

---

## Architecture

The competitive analysis operates in **four phases**:

```
┌─────────────────────────────────────────────────────────────┐
│              PHASE 1: INTELLIGENCE GATHERING                │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│   │  Slack  │    │   Web   │    │ Internal│               │
│   │ #strategy│    │ Search  │    │  Docs   │               │
│   └────┬────┘    └────┬────┘    └────┬────┘               │
│        └──────────────┼──────────────┘                      │
│                       ▼                                      │
│              Market Intelligence                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              PHASE 2: MULTI-MODEL ANALYSIS                  │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│   │ council │    │/kamikaze│    │  Claude │               │
│   │ 3 models│    │ 5 rounds│    │Synthesis│               │
│   └────┬────┘    └────┬────┘    └────┬────┘               │
│        └──────────────┼──────────────┘                      │
│                       ▼                                      │
│              Strategic Consensus                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│        PHASE 3: RAISE INTEGRATION (if requested)           │
│   ┌─────────────────────────────────────────────────┐      │
│   │ ~/yourco/raise/ docs → Acquirer matrix            │      │
│   │ M&A positioning → Investor targeting            │      │
│   │ Use of funds → Comparable acquisitions          │      │
│   └─────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              PHASE 4: REPORT GENERATION                     │
│   Markdown → PDF → Save to ~/yourco/docs/                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow

### Phase 1: Intelligence Gathering

1. **Slack Channel Scan**
   ```bash
   # Check #strategy channel for recent intel
   mcp__slack__slack_get_channel_history channel_id="C0XXXXXXXXX" limit=20
   ```

2. **Web Research**
   - Search for recent competitor news
   - Check funding announcements
   - Review product launches

3. **Internal Docs Check**
   - Confluence pages
   - Previous analysis reports
   - Fundraising strategy docs

### Phase 2: Multi-Model Analysis

1. **Run AI Council** (the council layer ships inside the kamikaze skill)
   ```bash
   python3 ~/.claude/skills/kamikaze/utils/council_query.py \
     "Analyze [Company]'s competitive position in [Market]" \
     "[Context from Phase 1]" \
     --full-council
   ```

2. **Run Kamikaze Deliberation**
   ```bash
   python3 ~/.claude/skills/kamikaze/utils/kamikaze_orchestrator_v4.py \
     --topic "[Strategic question]" \
     --template strategy \
     --depth standard \
     --output-dir ~/yourco/docs/kamikaze
   ```

### Phase 3: Raise Integration (Optional)

When `--include-raise` or user requests fundraising angle:

1. **Pull Raise Strategy Docs**
   - `~/yourco/raise/fundraising_30_60_day_roadmap.md`
   - `~/yourco/raise/MA_POSITIONING_GUIDE.md`
   - `~/yourco/raise/INVESTOR_MESSAGING_GUIDE.md`

2. **Generate Integration Content**
   - Three-phase raise structure
   - Target acquirer matrix with valuations
   - Comparable acquisitions table
   - Investor tiering by strategic value
   - Use of funds breakdown

### Phase 4: Report Generation

1. **Generate Markdown Report**
   ```
   ~/yourco/docs/competitive-analysis-[topic]-[YYYYMMDD].md
   ```

2. **Convert to PDF**
   ```bash
   pandoc [report].md -o [report].pdf --pdf-engine=xelatex \
     -V geometry:margin=1in -V fontsize=11pt
   ```

---

## Report Template

```markdown
# [Market] Competitive Landscape
## Strategic Assessment & Positioning

**CONFIDENTIAL // [STAGE] STRATEGY**

---

**DATE:** [Date]
**FROM:** Strategic Analysis (AI Council + Kamikaze Deliberation)
**SUBJECT:** [Topic]

---

## Executive Summary
[Key findings and consensus recommendation]

## 1. The Market Shift
[Critical developments and market map]

## 2. Competitor Deep Dive
[Per-competitor analysis with threat levels]

## 3. Investor Landscape
[Pre-seed targeting and raise structure]

## 3.5 Fundraising Strategy (if --include-raise)
[Three-phase raise, investor tiering, use of funds]

## 4. True Defensibility Assessment
[What IS vs IS NOT defensible]

## 5. Strategic Pivot Recommendation
[New positioning and pitch framework]

## 6. 90-Day Action Plan
[Phased milestones with success metrics]

## 7. Risk Matrix
[Probability, impact, mitigation]

## 8. Final Assessment
[Bottom line and win condition]

## 9. M&A Positioning (if --include-raise)
[Acquirer matrix, comparables, timeline]

## Appendix: Sources
[AI Council participants, Kamikaze rounds, web sources]
```

---

## CLI Usage

```bash
# Full analysis with raise integration
python3 ~/.claude/skills/competitive-analysis/utils/competitive_analyzer.py \
  --topic "AI Advertising Market" \
  --company "YourCompany" \
  --include-raise \
  --output ~/yourco/docs/

# Quick competitive scan (no kamikaze)
python3 ~/.claude/skills/competitive-analysis/utils/competitive_analyzer.py \
  --topic "AI Advertising Market" \
  --mode quick

# Deep analysis with exhaustive kamikaze
python3 ~/.claude/skills/competitive-analysis/utils/competitive_analyzer.py \
  --topic "AI Advertising Market" \
  --depth exhaustive
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--topic` | Market/industry to analyze | Required |
| `--company` | Your company for positioning | Optional |
| `--competitors` | Comma-separated competitor list | Auto-discovered |
| `--include-raise` | Add fundraising strategy sections | False |
| `--mode` | quick, standard, exhaustive | standard |
| `--output` | Output directory | ~/yourco/docs/ |

---

## Important Rules

### DO:
- Gather fresh market intelligence before analysis
- Run both the AI council layer AND /kamikaze for major analyses
- Include competitor funding and reach metrics
- Cross-reference with internal docs
- Generate PDF for sharing

### DON'T:
- Skip intelligence gathering (stale data = bad analysis)
- Run without context (provide company background)
- Ignore minority opinions from kamikaze
- Share raw outputs without synthesis

---

## Security Notes

**NEVER include in analysis prompts:**
- API keys, passwords, tokens
- Customer PII or confidential data
- Unreleased product details
- Internal financial projections

**Safe to include:**
- Public competitor information
- Published funding announcements
- Industry reports and benchmarks
- General strategic questions

---

## Integration with Other Skills

This skill integrates with:
- **council** (ships in `kamikaze/utils/`): Multi-model parallel opinions
- **kamikaze**: Recursive strategic deliberation
- **gemini/openai/grok**: Individual model queries

Typical flow:
```
/competitive-analysis → AI council → /kamikaze → Report
```

---

## Example Invocation

```bash
/competitive-analysis "AI Advertising Market" --include-raise
```

This will:
1. Scan Slack #strategy for recent intel
2. Web search Koah, OpenAI, Viant news
3. Run AI Council with competitive prompt
4. Run Kamikaze V4 strategy template
5. Pull ~/yourco/raise/ docs for M&A positioning
6. Generate markdown + PDF report
7. Save to ~/yourco/docs/

---

## Version History

- **v1.0.0** (Jan 2026): Initial release with council + kamikaze + raise integration

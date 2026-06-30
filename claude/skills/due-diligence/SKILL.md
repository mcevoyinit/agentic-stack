---
name: due-diligence
description: |
  Comprehensive investment due diligence orchestrator for any company
  (startup, private, or public). Stage-conditioned, upside-maximizing
  architecture that identifies "spiky traits" and surfaces conflicts
  rather than smoothing narratives. Invokes sister skills (/cap-table,
  /tokenomics, /person-research, /competitive-analysis) for targeted
  deep-dives. Outputs Upside Thesis vs Downside Protection matrix.
  Trigger: "due diligence", "DD on", "diligence on", "investment research",
  "should I invest in", "evaluate this company", "deal review".
  DO NOT activate for: Simple company overviews, stock price checks,
  or general "tell me about X" queries.
---

# Due Diligence — Investment Research Orchestrator

> Due diligence in venture capital is not a process of eliminating bad options —
> it is a hypothesis generator for outlier potential. Startups are bundles of
> fatal flaws offset by singular superpowers. The AI must find the one
> overriding reason to say "Yes" and surface every risk to price in.

## Activation

```
ACTIVATE when user says:
  "due diligence", "DD on [company]", "diligence on", "investment research",
  "should I invest in", "evaluate this company", "deal review",
  "investment memo for", "diligence report"

DO NOT activate for:
  - Simple company overview → use WebSearch or /software-estate
  - Stock price or valuation only → use WebSearch or /cap-table
  - "Tell me about X" without investment context → skip
  - Competitive landscape only → use /competitive-analysis
```

## Input

User provides a **company name** (required) and optionally:
- Stage context ("seed stage", "Series C", "pre-IPO")
- Sector hint ("crypto", "SaaS", "biotech", "hardware")
- Specific focus area ("I'm worried about the team")
- Data room files (PDFs, Excel) for private company deep-dives
- Investment thesis to validate ("I think their moat is X")

If no company is clear, ask: "Which company should I run diligence on?"

---

## Core Design Principles

### 1. Upside-Maximizing, Not Risk-Sieving
The skill does NOT produce a pass/fail verdict. It produces an **Upside Thesis vs. Downside Protection Matrix**. Every startup has red flags — the question is whether the upside compensates.

### 2. Stage-Conditioned Analysis
Different stages demand different lenses:

| Stage | Primary Focus (80%) | Secondary (20%) |
|-------|--------------------|--------------------|
| Pre-Seed / Seed | Founders + Market Timing | Product vision, early traction |
| Series A | Product-Market Fit signals | Team scaling, unit economics hints |
| Series B-C | Unit economics, retention cohorts | Competitive moat, CAC/LTV |
| Late / Pre-IPO | Financial performance, governance | Regulatory, public market readiness |

### 3. Conflict Surfacing Over Narrative Smoothing
LLMs default to sycophantic consensus. This skill MUST surface raw discrepancies:
```
⚠ [CONFLICT]: Crunchbase lists Series A at $15M. TechCrunch article says $12M.
⚠ [CONFLICT]: Founder claims 10x YoY growth. Glassdoor reviews mention layoffs.
```
Never average conflicting numbers. Present both with sources.

### 4. Negative Space Detection
Explicitly flag what is MISSING:
```
⚠ [MISSING]: No technical co-founder listed for an AI infrastructure company
⚠ [MISSING]: No pricing page for a 3-year-old SaaS product
⚠ [MISSING]: No GitHub repository for an "open-source" protocol
⚠ [MISSING]: Team page lists 4 people but LinkedIn shows 15+ employees
```

### 5. Hypothesis-Driven Sister Skill Routing
When invoking sister skills, pass the current hypothesis:
- "Run `/person-research` on [founder] — Phase 1 suggests high executive churn"
- "Run `/tokenomics` on [protocol] — Phase 2 found anomalous insider allocation"
- "Run `/cap-table` on [company] — founder appears to have very low ownership for stage"

---

## Research Architecture (5 Steps)

```
┌──────────────────────────────────────────────────────────────────┐
│                    DUE DILIGENCE ORCHESTRATOR                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 1: CLASSIFY & FRAME       Stage, sector, thesis hypothesis │
│  ────────────────────────                                        │
│                                                                  │
│  Step 2: GESTALT SCAN           Holistic first-pass across all   │
│  ─────────────────────          dimensions simultaneously        │
│                                                                  │
│  Step 3: SPIKY TRAIT ID         Find the outlier strength that   │
│  ───────────────────────        justifies the investment thesis  │
│                                                                  │
│  Step 4: SHADOW DATA &          Unvarnished sentiment, missing   │
│          NEGATIVE SPACE         data, conflict surfacing         │
│  ─────────────────────                                           │
│                                                                  │
│  Step 5: SYNTHESIS              Upside/Downside matrix, risks    │
│  ────────────────────           to price in, backchanneling guide│
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Step 1: CLASSIFY & FRAME

### Goal
Determine the company's stage, sector, and load the correct analytical lens.

### WebSearch Queries
```
"[COMPANY]" founded OR "series" OR funding crunchbase
"[COMPANY]" CEO founder team
"[COMPANY]" product OR platform OR protocol description
"[COMPANY]" revenue OR ARR OR users OR TVL
```

### Classification Output

```
Company:    [NAME]
Sector:     [SaaS / Crypto-L1 / Crypto-DeFi / Biotech / DeepTech / Consumer /
             Marketplace / Fintech / Hardware / Other]
Stage:      [Pre-Seed / Seed / Series A / Series B / Series C+ / Late / Public]
Founded:    [YEAR]
HQ:         [LOCATION]
Employees:  [EST. COUNT]
Last Round: [ROUND, AMOUNT, DATE, LEAD]

Analysis Lens Loaded: [Stage-appropriate focus areas per table above]
```

### Sector-Specific Routing
- **Crypto/Web3** → Queue `/tokenomics` for Step 3 deep-dive
- **SaaS/Fintech** → Queue `/competitive-analysis` for Step 3
- **All stages** → Queue `/cap-table` for Step 3
- **Any stage** → Queue `/person-research` on founders for Step 3

---

## Step 2: GESTALT SCAN

### Goal
Build a holistic first-pass across ALL dimensions simultaneously. Do NOT evaluate sequentially — strengths in one area compensate for weaknesses in another.

### 2A. Team & Founders

**WebSearch Queries:**
```
"[FOUNDER NAME]" background career education
"[FOUNDER NAME]" previous company exit acquisition
"[FOUNDER NAME]" "[CO-FOUNDER NAME]" worked together before
"[COMPANY]" "VP of" OR "Head of" OR "CTO" hire
"[COMPANY]" executive team leadership
site:linkedin.com "[COMPANY]" "[FOUNDER NAME]"
```

**Capture:**
- Founder backgrounds (education, prior companies, domain expertise)
- Founder-market fit: Have they lived the problem they're solving?
- Co-founder history: Have they worked together before? (Lindy Effect)
- Key executive hires and tenure (VP Eng, VP Sales, CFO)
- Executive churn signal: Has any C-suite role been filled 2+ times?
- Board composition (if known)

### 2B. Product & Technology

**WebSearch Queries:**
```
"[COMPANY]" product demo launch
"[COMPANY]" customers OR users OR clients
"[COMPANY]" technology stack OR architecture
"[COMPANY]" open source github
"[COMPANY]" patents filed OR intellectual property
"[COMPANY]" product review OR comparison site:g2.com OR site:capterra.com
site:news.ycombinator.com "[COMPANY]"
```

**Capture:**
- What the product actually does (in plain language)
- Product-market fit signals (waitlists, organic growth, retention mentions)
- Technical moat assessment (proprietary tech, network effects, data moat, switching costs)
- Open-source vs. proprietary strategy
- Patent portfolio (if applicable)
- User/customer sentiment from review sites

### 2C. Market & Timing

**WebSearch Queries:**
```
"[COMPANY]" market size TAM OR "total addressable"
"[COMPANY]" competitors landscape
"[COMPANY]" industry trend OR tailwind
"[COMPANY]" regulatory environment
"[SECTOR]" market growth forecast 2025 2026 2027
```

**Capture:**
- Market size estimates (if available — often not for novel categories)
- Key competitors and their funding/traction
- Timing assessment: Is the market ready NOW? Too early? Too late?
- Secular tailwinds or headwinds
- Regulatory environment (friendly, hostile, uncertain)

### 2D. Business Model & Financials (Public Data Only)

**WebSearch Queries:**
```
"[COMPANY]" revenue OR ARR OR GMV OR TVL
"[COMPANY]" pricing model subscription OR usage
"[COMPANY]" business model monetization
"[COMPANY]" profitability OR burn rate
"[COMPANY]" growth rate "year over year" OR "YoY"
```

**Capture:**
- Revenue model type (subscription, usage, marketplace take-rate, token, protocol fees)
- Any publicly reported financial metrics
- Growth trajectory signals
- Path to profitability narrative
- **Tag all financial estimates as `[UNVERIFIED — REQUIRES DATA ROOM]`**

### 2E. Cap Table & Governance (Overview)

**WebSearch Queries:**
```
"[COMPANY]" investors funding rounds
"[COMPANY]" founder ownership stake
"[COMPANY]" board of directors governance
"[COMPANY]" total funding raised
```

**Capture:**
- Investor roster and quality
- Total capital raised
- Any known ownership data
- Board composition signals
- **Queue `/cap-table` for deep-dive in Step 3 if data is sparse**

---

## Step 3: SPIKY TRAIT IDENTIFICATION & SISTER SKILL ROUTING

### Goal
From the Gestalt scan, identify the ONE outlier trait that could make this a generational investment. Then invoke sister skills for hypothesis-driven deep-dives.

### Spiky Trait Categories

| Trait Type | Signal | What to Look For |
|---|---|---|
| **Founder-Market Fit** | Founder previously built/sold company in exact same space | Deep domain expertise, repeat founder in sector |
| **Technical Moat** | Proprietary technology that's 10x better, not 2x | Patents, novel architecture, data advantage |
| **Network Effects** | Product gets better with more users | Marketplace dynamics, protocol adoption |
| **Explosive Traction** | Growth rate that defies the stage | 3x+ YoY at scale, viral coefficient |
| **Timing** | Regulatory/technology shift that just unlocked the market | New law, new infrastructure, new behavior |
| **Distribution Advantage** | Built-in access to customers others can't reach | Platform integrations, partnerships, community |

### Thesis Statement (MANDATORY)
After identifying the spiky trait, write a one-sentence investment thesis:
```
THESIS: "[COMPANY] could be a [X]x outcome because [SPIKY TRAIT],
despite [BIGGEST RISK], which can be mitigated by [MITIGATION]."
```

### Sister Skill Routing (Hypothesis-Driven)

Route to sister skills based on what the Gestalt scan revealed:

| If Gestalt Found... | Invoke | With Hypothesis |
|---|---|---|
| Anomalous founder background | `/person-research` | "Investigate [specific concern or strength]" |
| Crypto/token component | `/tokenomics` | "Focus on [insider allocation / governance / liquidity]" |
| Sparse ownership data | `/cap-table` | "Reconstruct ownership, check for [dilution / control concerns]" |
| Strong competitor landscape | `/competitive-analysis` | "Benchmark against [specific competitors]" |
| Market size uncertainty | `/market-size` (if available) | "Bottom-up TAM for [specific segment]" |

---

## Step 4: SHADOW DATA & NEGATIVE SPACE

### Goal
Find unvarnished truth that doesn't appear in press releases. Surface missing data.

### Shadow Data WebSearch Queries (MANDATORY — run ALL)

**Culture & Team Sentiment:**
```
site:teamblind.com "[COMPANY]"
site:glassdoor.com "[COMPANY]" reviews
"[COMPANY]" layoffs OR restructuring OR "let go"
"[COMPANY]" "culture" OR "work-life" OR "toxic" site:reddit.com
```

**Product & Customer Sentiment:**
```
site:reddit.com "[COMPANY]" ("sucks" OR "alternative" OR "migrated" OR "switched to")
site:news.ycombinator.com "[COMPANY]"
"[COMPANY]" vs "[COMPETITOR]" review OR comparison
"[COMPANY]" complaints OR issues OR bugs
```

**Legal & Regulatory:**
```
"[COMPANY]" lawsuit OR litigation OR "v." OR sued
"[COMPANY]" SEC OR regulatory OR investigation OR fine
"[COMPANY]" patent infringement OR IP dispute
"[FOUNDER NAME]" lawsuit OR fraud OR controversy
```

### Negative Space Checklist (Flag if MISSING)

| Expected Data Point | Missing = Red Flag Because |
|---|---|
| Technical co-founder (for tech company) | No one to build/maintain the core product |
| Pricing page (SaaS, 2+ years old) | Product may not be ready for market |
| Public GitHub (for "open-source" claims) | Open-source claim may be vaporware |
| Customer logos or case studies | May not have real customers |
| Team page with photos/bios | Hiding team composition |
| Board members listed | Governance may be informal |
| Privacy policy / Terms of Service | Legal maturity concerns |
| Revenue/traction metrics (Series B+) | Not proud of the numbers |

---

## Step 5: SYNTHESIS — Final Output

### 5A. Company Snapshot

```
Company:        [NAME]
Sector:         [SECTOR]
Stage:          [STAGE]
Founded:        [YEAR] by [FOUNDERS]
HQ:             [LOCATION]
Employees:      [COUNT] ([source])
Last Round:     [DETAILS]
Total Raised:   $[X] from [KEY INVESTORS]
```

### 5B. Investment Thesis

```
THESIS: "[One sentence thesis statement from Step 3]"

SPIKY TRAIT: [The outlier strength]
CONVICTION LEVEL: [HIGH / MEDIUM / LOW] — because [reasoning]
```

### 5C. Upside Thesis vs. Downside Protection Matrix (MANDATORY)

| Dimension | Upside Case | Downside Case | Current Evidence | Weight |
|---|---|---|---|---|
| Team | [Best case] | [Worst case] | [What we actually found] | [HIGH/MED/LOW] |
| Product/Tech | ... | ... | ... | ... |
| Market/Timing | ... | ... | ... | ... |
| Business Model | ... | ... | ... | ... |
| Financials | ... | ... | ... | ... |
| Cap Table | ... | ... | ... | ... |
| Regulatory | ... | ... | ... | ... |
| Strategic | ... | ... | ... | ... |

### 5D. Conflicts Detected

| Data Point | Source A | Source B | Severity | Resolution Needed |
|---|---|---|---|---|
| Valuation | Crunchbase: $X | TechCrunch: $Y | MEDIUM | Ask company |
| Employee count | LinkedIn: X | Team page: Y | LOW | Minor discrepancy |

*If no conflicts: "No data conflicts detected across [N] sources."*

### 5E. Negative Space — What's Missing

| Missing Data Point | Expected For This Stage/Sector | Risk Implication |
|---|---|---|
| [item] | [why expected] | [what it might mean] |

### 5F. Risks to Price In (NOT Kill Criteria)

| Risk | Severity | Likelihood | Mitigable? | How to Mitigate |
|---|---|---|---|---|
| [risk 1] | HIGH/MED/LOW | HIGH/MED/LOW | Yes/No/Partially | [approach] |
| [risk 2] | ... | ... | ... | ... |

### 5G. Key Questions for Management

Generate 5-10 targeted questions based on gaps and risks found:
```
1. [Question targeting specific gap or risk]
2. [Question about conflict discovered]
3. [Question about negative space finding]
...
```

### 5H. Customer Backchanneling Guide

Based on product weaknesses and competitive positioning, generate:
```
Target customers to backchannel: [types/profiles]

Questions to ask:
1. "How did you evaluate [COMPANY] vs [COMPETITOR]?"
2. "What would cause you to switch away?"
3. "How critical is [PRODUCT] to your workflow — nice-to-have or mission-critical?"
4. [Additional targeted questions based on DD findings]
```

### 5I. Data Gaps & Required Data Room Items

```
TO VERIFY IN DATA ROOM:
- [ ] Audited financials / P&L for last 2 years
- [ ] Customer cohort retention data
- [ ] Cap table (fully diluted, including options/warrants)
- [ ] Key customer contracts and concentration
- [ ] Employment agreements and IP assignment
- [ ] Material contracts and vendor dependencies
- [ ] Pending litigation or regulatory matters
- [Additional items based on specific gaps found]
```

### 5J. Sources

```
Company Sources:
  - [urls]

Press / News:
  - [urls]

Shadow Data:
  - [urls]

Data Providers:
  - [urls]

Sister Skill Reports:
  - /cap-table output: [summary]
  - /person-research output: [summary]
  - /tokenomics output: [summary] (if applicable)
```

---

## Anti-Patterns (DO NOT)

| Anti-Pattern | Why It Fails |
|---|---|
| Producing a pass/fail verdict | Violates VC power law — outliers always look flawed |
| Treating red flags as kill criteria | Strengths compensate for weaknesses — present as "risks to price in" |
| Averaging conflicting data points | Destroys signal — surface the raw conflict |
| Scraping for private financial metrics | Private companies don't publish CAC/LTV — tag as `[REQUIRES DATA ROOM]` |
| Smoothing narrative into consensus | LLM default — enforce Conflict Surfacing |
| Sequential elimination funnel | Breaks the Gestalt — evaluate all dimensions simultaneously |
| Generic prompts to sister skills | Pass the current hypothesis for dramatically better signal |
| Treating all sources equally | Founder tweets may be more accurate than Crunchbase for early-stage |
| Ignoring what's missing | Negative space is often more revealing than what's present |
| Making an investment recommendation | The skill surfaces data and structure — the human decides |

---

## Example Invocations

```
User: "DD on Anthropic"
→ Classify: Late-stage AI/DeepTech. Load late-stage lens.
→ Gestalt: Team (Dario/Daniela ex-OpenAI), Product (Claude), Market (massive)
→ Spiky trait: Technical moat + founder pedigree
→ Sister skills: /cap-table, /person-research on founders
→ Shadow data: Glassdoor, Reddit, legal searches

User: "due diligence on Tempo blockchain"
→ Classify: Crypto-L1, well-funded (Series A)
→ Route to /tokenomics immediately
→ Focus: Team (Farcaster acquisition), token distribution, governance

User: "should I invest in this seed-stage fintech"
→ Classify: Seed, Fintech
→ Load seed lens: 80% team + market, 20% product vision
→ Spiky trait hunting on founders
→ Heavy shadow data and negative space checks

User: "deal review on [Series C SaaS company]"
→ Classify: Series C, SaaS
→ Load growth lens: 80% unit economics + retention
→ Flag all financial metrics as [REQUIRES DATA ROOM]
→ Competitive moat analysis via /competitive-analysis
```

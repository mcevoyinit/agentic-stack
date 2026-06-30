---
name: market-size
description: |
  Rigorous TAM/SAM/SOM estimation for any market using the "Constrained
  Potential" framework — caps bottom-up theoretical potential with top-down
  macro-budget limits. Incentive-adjusted sourcing tags all data with bias
  provenance. Exposes the "Fragile Variable" (most sensitive assumption),
  maps value-chain leakage, and handles novel markets via bifurcated B2B/B2C
  engines. 3-phase architecture with mandatory source triangulation.
  Trigger: "market size", "TAM", "SAM", "SOM", "total addressable market",
  "market sizing", "how big is the market", "market opportunity".
  DO NOT activate for: Simple revenue lookups, company valuations,
  competitive analysis, or financial modeling.
---

# Market Size — Constrained Potential Calculator

> Market sizing is not an exercise in finding a number — it is the
> construction of a defensible, constraint-bounded model of a business
> opportunity. The agent's job is to build a dynamic equation where every
> variable is exposed, every source is bias-tagged, and the single most
> fragile assumption is isolated for the human to stress-test.

## Activation

```
ACTIVATE when user says:
  "market size", "TAM", "SAM", "SOM", "total addressable market",
  "market sizing", "how big is the market", "market opportunity",
  "size the market for", "TAM/SAM/SOM", "serviceable addressable market",
  "market potential for [product]"

DO NOT activate for:
  - Company valuations or DCF models → out of scope
  - Competitive landscape / SWOT → use general research
  - Simple revenue lookups → use WebSearch directly
  - Financial projections or fundraising models → not a sizing skill
```

## Input

User provides a **product, market, or business description** (required) and optionally:
- Geographic scope ("US only", "global", "EU + LATAM")
- Customer type ("enterprise B2B", "consumer", "SMB")
- Time horizon ("current", "5-year projection")
- Focus ("just the bottom-up model", "novel market — no analyst coverage")

If the product is unclear, ask: "Describe the product/service and who the buyer is."

---

## Core Design Principle

**Constrained Potential Calculator, NOT Report Aggregator.**

Claude Code is a text-synthesis engine, not an analyst terminal. It cannot:
- Access paywalled Gartner/IBISWorld/Statista full reports
- Reliably scrape enterprise B2B pricing (hidden behind "Contact Sales")
- Query proprietary firmographic databases (ZoomInfo, PitchBook)

It CAN:
- Triangulate publicly available data across government, SEC, and press sources
- Detect circular sourcing chains and flag unverified estimates
- Build constraint-bounded models from census/BLS population data
- Cross-reference claimed TAMs against actual public company revenues
- Expose the fragile variables that make or break any market size claim

---

## Source Confidence & Bias Tagging System

| Tag | Source Type | Inherent Bias | When to Use |
|-----|------------|---------------|-------------|
| `[GOV_PRIMARY]` | Census, BLS, BEA, Eurostat | Low — methodology public | Population counts, wage data, industry output |
| `[SEC_FILING]` | 10-K, 10-Q, S-1 revenue segments | `Bias: Equity-Pump` for S-1 TAM claims; LOW for reported revenue | Actual revenue figures (reliable), TAM claims in S-1 (discount) |
| `[ANALYST_REPORT]` | Gartner, GVR, IDC, Mordor Intelligence | `Bias: Vendor-Inflation` — sell reports to vendors in the market | Top-down category sizing — always cross-reference, never sole source |
| `[PRESS_DERIVED]` | TechCrunch, Forbes, Bloomberg citing analysts | `Bias: Circular` — often cites analyst summaries, not methodology | Directional signal only — trace back to primary source |
| `[COMPANY_CLAIM]` | Pitch decks, investor presentations, blog posts | `Bias: Self-Serving` — companies inflate their own TAM | Note but heavily discount — compare against revenue ceiling |
| `[COMPUTED]` | Agent-derived arithmetic | `Bias: Compounding Error` — small input errors multiply | Always flag formula and inputs for user verification |
| `[UNKNOWN]` | Data not found after 3+ targeted searches | N/A | Mark cell, do not estimate or hallucinate |

**Critical rule**: Every number in the final output MUST carry a bias tag. Untagged numbers are not permitted.

---

## Research Architecture (3 Phases)

```
+------------------------------------------------------------------+
|                  CONSTRAINED POTENTIAL MODEL                       |
+------------------------------------------------------------------+
|                                                                    |
|  Phase 1: DATA GATHERING           Incentive-adjusted sourcing,   |
|  -----------------------           bias tagging, primary sources   |
|                                    only, geographic/reg gates     |
|                                                                    |
|  Phase 2: CONSTRAINED POTENTIAL    Bottom-up theoretical model    |
|  ---------------------------       capped by top-down macro        |
|                                    budget, "Do Nothing" discount  |
|                                                                    |
|  Phase 3: VALUE CHAIN &            Captured SAM, fragile          |
|  NARRATIVE SYNTHESIS               variable, revenue ceiling,     |
|  -----------------------           "Why Now", data gaps            |
|                                                                    |
+------------------------------------------------------------------+
```

---

## Phase 1: INCENTIVE-ADJUSTED DATA GATHERING

### Goal
Collect raw market data from primary sources, tag every data point with its bias provenance, and identify geographic/regulatory gates that zero out portions of the TAM.

### WebSearch Query Templates

**Government / Census / BLS (highest trust):**
```
site:bls.gov "[INDUSTRY]" OR "[JOB_ROLE]" employment statistics
site:census.gov "[INDUSTRY]" "annual business survey" OR "economic census"
site:bea.gov "[INDUSTRY]" GDP contribution OR output
"Bureau of Labor Statistics" "[JOB_ROLE]" "occupational outlook" salary
```

**SEC Filings (actual revenue, not TAM claims):**
```
site:sec.gov 10-K "[COMPETITOR]" "revenue" "[PRODUCT_CATEGORY]"
site:sec.gov S-1 "[MARKET_CATEGORY]" "total addressable market"
"[PUBLIC_COMP]" 10-K "market opportunity" OR "addressable market"
```

**Analyst Reports (use with vendor-inflation discount):**
```
"[MARKET]" market size 2025 OR 2026 CAGR forecast
"[MARKET]" "total addressable market" billion site:grandviewresearch.com
"[MARKET]" Gartner OR IDC OR Forrester market forecast
```

**Competitor Revenue / Pricing Signals:**
```
"[COMPETITOR]" pricing OR "per seat" OR "per month"
"[COMPETITOR]" ARR OR "annual recurring revenue" OR revenue growth
site:getlatka.com "[COMPETITOR]" OR site:sacra.com "[COMPETITOR]"
```

**Novel Market / Category Creation:**
```
"[MANUAL_PROCESS]" "cost of" OR "average time" OR "salary" site:bls.gov
"[ADJACENT_MARKET]" market size 2025 2026 — analogous proxy
"[STATUS_QUO_TOOL]" users OR customers OR market penetration
```

### Source Triangulation Rule (MANDATORY)
1. Find the **primary source** — who originally calculated the number?
2. If analyst firm: is the methodology public? If not, tag `[PRESS_DERIVED]`
3. Cross-reference against at least one independent source
4. If citation chain is circular, note: "Circular sourcing suspected"

### Geographic & Regulatory Gates
Before Phase 2, zero out TAM in jurisdictions where the product cannot legally operate. Flag language barriers and infrastructure prerequisites (e.g., broadband penetration).

---

## Phase 2: THE CONSTRAINED POTENTIAL CALCULATION

### Goal
Build the core TAM/SAM/SOM model using the "Constrained Potential" framework: cap bottom-up theoretical potential with top-down macro-budget limits.

### Step 1: Bottom-Up Theoretical Potential

**For Established Markets:**
```
Theoretical TAM = Target Buyers (N) x Estimated Annual Contract Value (ACV)

Where:
  N = Population of qualified buyers (from BLS, Census, or industry data)
  ACV = Median price point from public pricing pages, SEC revenue/customer
        disclosures, or analyst-estimated category spend per seat
```

**For Novel Markets (B2B) — "Cost of Status Quo" Engine:**
```
Theoretical TAM = Affected Workers (N) x Hours Saved/Year x Fully Loaded Wage/Hour

Where:
  N = BLS employment count for affected job roles
  Hours Saved = Estimated efficiency gain (STATE YOUR ASSUMPTION)
  Wage = BLS median hourly wage + 30% benefits loading
```

**For Novel Markets (B2C) — "Share of Time & Attention" Engine:**
```
Theoretical TAM = Target Population (N) x Share of Wallet/Time x Monetization Rate

Where:
  N = Census/demographic population matching target profile
  Share of Wallet = % of existing spend category being redirected
  Monetization Rate = Revenue per user (from analogous platforms)
```

### Step 2: Top-Down Macro-Budget Constraint

Identify the total departmental or category budget pool that constrains the bottom-up figure:
```
Macro Budget = Total industry/department spend in target category (from BEA,
               Gartner IT Spending, corporate budget surveys)

Constraint Test: If Theoretical TAM > 25% of Macro Budget → FLAG
  "Bottom-up model implies capturing [X]% of all [category] spend.
   This violates zero-sum budget constraints. Apply ceiling."
```

### Step 3: The Collision — Constrained TAM

```
Constrained TAM = MIN(Bottom-Up Theoretical, Top-Down Macro Budget x Penetration Cap)
```

### Step 4: SAM Calculation with "Do Nothing" Discount

```
SAM = Constrained TAM
      - Geographic/Regulatory Gates (from Phase 1)
      - "Do Nothing" Discount (non-consumption segment)
      - Segment Mismatch (wrong company size, wrong vertical, etc.)

The "Do Nothing" segment = buyers who will refuse to adopt and stick to
  Excel/manual processes/status quo. Default assumption: 30-60% of
  theoretical buyers in enterprise B2B, 50-80% in SMB. STATE YOUR
  ASSUMPTION and expose it as a variable.
```

### Step 5: SOM Estimation

```
SOM = SAM x Realistic Capture Rate

Where Capture Rate considers:
  - Current competitive landscape (# of funded competitors)
  - Go-to-market maturity (pre-revenue vs. scaling)
  - Distribution advantage or constraint
  - Typical 3-5 year capture for category entrant: 1-5% of SAM
```

### Output Table — Constrained Potential

| Layer | Value | Methodology | Key Assumption | Bias Tag |
|-------|-------|-------------|----------------|----------|
| Bottom-Up Theoretical TAM | $X | N x ACV | [assumption] | [COMPUTED] |
| Top-Down Macro Budget | $X | [category] total spend | [source] | [tag] |
| **Constrained TAM** | $X | MIN(BU, TD x cap) | Penetration cap = X% | [COMPUTED] |
| Geographic/Reg Gate Discount | -$X | [jurisdictions excluded] | [rationale] | [GOV_PRIMARY] |
| "Do Nothing" Discount | -$X | X% non-adoption | [assumption] | [COMPUTED] |
| **Core SAM** | $X | Constrained - gates - non-adoption | | [COMPUTED] |
| Adjacent TAM (SEPARATE) | $X | [new geos / new products] | [assumption] | [COMPUTED] |
| **SOM (3-Year)** | $X | SAM x capture rate | Capture = X% | [COMPUTED] |

**Critical**: Core TAM and Adjacent TAM MUST be presented in separate rows. Never sum them without explicit justification.

---

## Phase 3: VALUE CHAIN & NARRATIVE SYNTHESIS

### 3A. Market Definition & Scope

```
Market:           [DESCRIPTION]
Product:          [WHAT IS BEING SOLD]
Buyer:            [WHO PAYS — job title, company type, consumer profile]
Geography:        [TARGET MARKETS]
Time Horizon:     [CURRENT / 5-YEAR]
Market Maturity:  [Nascent / Growth / Mature / Declining]
```

### 3B. Value Chain Map (MANDATORY)

Map where dollars leak before reaching the product company:

| Value Chain Layer | % of End-Customer Spend | Example | Implication |
|---|---|---|---|
| Cloud Infrastructure (AWS/GCP/Azure) | X% | Hosting, compute, storage | Not capturable by application vendor |
| Distribution / Marketplace (App Store, AWS Mktplace) | X% | 15-30% take rate | Reduces effective revenue per customer |
| Implementation / Services (Accenture, agencies) | X% | Customization, integration | May exceed software cost for enterprise |
| Channel Partners / Resellers | X% | VAR margins, SI fees | Revenue share reduces capture |
| **Available to Product Company** | **X%** | | **Captured SAM = Core SAM x this %** |

```
Captured SAM = Core SAM x (100% - Value Chain Leakage%)
```

### 3C. Fragile Variable Analysis (MANDATORY)

Identify the single variable with the highest sensitivity — the assumption that, if wrong by 2x, changes the conclusion:

```
FRAGILE VARIABLE: [Name]
Current Assumption: [Value]
If 2x Higher: TAM becomes $X → Implication: [narrative]
If 2x Lower:  TAM becomes $X → Implication: [narrative]
Source Quality: [tag] — [why this variable is hard to pin down]
Testable Via:   [How the user could validate this assumption]
```

### 3D. Comparable Revenue Ceiling Test (MANDATORY)

```
Top 5 Public Companies in Adjacent/Overlapping Space:

| Company | Relevant Revenue Segment | Annual Revenue | Source | Bias Tag |
|---------|-------------------------|----------------|--------|----------|
| [Comp1] | [segment] | $X | 10-K FY[YEAR] | [SEC_FILING] |
| [Comp2] | [segment] | $X | 10-K FY[YEAR] | [SEC_FILING] |
| ... | | | | |
| **Sum of Top 5** | | **$X** | | |

Revenue Ceiling Ratio = Claimed TAM / Sum of Top 5 Revenue
If Ratio > 50x → FLAG: "Theoretical TAM exceeds observable captured
  revenue by [X]x. Justify gap: [fragmentation / nascent / methodology flaw]"
If Ratio 10-50x → NOTE: "Market is early-stage or highly fragmented"
If Ratio < 10x → HEALTHY: "TAM is grounded in observable revenue"
```

### 3E. Novel Market Sizing (if applicable)

Only output this section when no established analyst coverage exists.

**B2B — Cost of Status Quo Model:**

| Component | Value | Source | Bias Tag |
|-----------|-------|--------|----------|
| Affected job role(s) | [role] | BLS OOH | [GOV_PRIMARY] |
| Employment count (N) | X | BLS | [GOV_PRIMARY] |
| Median hourly wage | $X | BLS | [GOV_PRIMARY] |
| Fully loaded cost (wage x 1.3) | $X | Standard loading | [COMPUTED] |
| Hours saved per worker/year | X | **STATE ASSUMPTION** | [COMPUTED] |
| **B2B Novel TAM** | **$X** | N x Hours x Loaded Wage | [COMPUTED] |

**B2C — Share of Time & Attention Model:**

| Component | Value | Source | Bias Tag |
|-----------|-------|--------|----------|
| Target demographic | [description] | Census | [GOV_PRIMARY] |
| Population (N) | X | Census | [GOV_PRIMARY] |
| Analogous platform ARPU | $X | [platform] 10-K | [SEC_FILING] |
| Share capture assumption | X% | **STATE ASSUMPTION** | [COMPUTED] |
| **B2C Novel TAM** | **$X** | N x ARPU x Share% | [COMPUTED] |

### 3F. Growth Drivers & "Why Now" (MANDATORY)

| Driver | Evidence | Maturity | Impact on TAM | Source |
|--------|----------|----------|---------------|--------|
| [Enabling tech] | [metric] | Early/Growth/Mature | Expands TAM by X% | [tag] |
| [Regulatory shift] | [policy] | Pending/Active | Opens [geo] market | [tag] |
| [Behavioral trend] | [data] | Nascent/Mainstream | Increases adoption by X% | [tag] |
| [Cost decline] | [metric] | Accelerating/Stable | Induces demand in [segment] | [tag] |

If no compelling "Why Now" exists, state: "No clear inflection point identified — market may be accessible but not accelerating."

### 3G. Data Gaps & Stale Data Warnings (MANDATORY)

```
- [GAP]: [Specific data point not found — what it would change]
- [STALE]: [Source from YYYY — lag X months, sector may have shifted]
- [CIRCULAR]: [Source X cites Source Y which cites Source X]
- [PAYWALL]: [Full methodology behind [report] not accessible]
- If any source > 24 months old in a hyper-growth sector: FLAG AS STALE
```

### 3H. Sources (with Bias Tags)

```
Government / Primary Data:
  - [url] [GOV_PRIMARY]
  - [url] [GOV_PRIMARY]

SEC Filings (Revenue = reliable, TAM claims = discount):
  - [url] [SEC_FILING] — revenue figures used
  - [url] [SEC_FILING] — TAM claim noted, Bias: Equity-Pump

Analyst Reports (Vendor-Inflation discount applied):
  - [url] [ANALYST_REPORT] — Bias: Vendor-Inflation
  - Methodology verified: Yes/No

Press / Industry:
  - [url] [PRESS_DERIVED] — primary source traced: Yes/No

Company Claims:
  - [url] [COMPANY_CLAIM] — Bias: Self-Serving
```

---

## Anti-Patterns (DO NOT)

| Anti-Pattern | Why It Fails |
|---|---|
| Citing a TAM number without methodology or source | Investors instantly dismiss unsourced claims — always show the math |
| Treating Gartner/GVR as objective truth | Vendor-driven inflation — they sell reports to vendors in the market |
| Using S-1 TAM claims as ground truth | Equity-driven inflation — protected by forward-looking safe harbors |
| Confusing TAM with SAM | TAM = everyone who theoretically could buy; SAM = everyone you can actually reach and sell to |
| Summing Core TAM + Adjacent TAM into one number | Adjacent markets are speculative — must be separated and labeled |
| Bottom-up without top-down constraint | Leads to "$50B TAM" that requires 33% of all industry spend — spreadsheet delusion |
| Top-down without bottom-up grounding | Leads to lazy "Gartner says $200B" with no unit economics — narrative without math |
| Single-source estimates | Circular sourcing is the #1 AI failure mode — always triangulate |
| Ignoring the "Do Nothing" competitor | Non-consumption (Excel/manual/status quo) is the largest segment in most B2B SAMs |
| Scraping B2B pricing as if it were public | Enterprise pricing is hidden, customized, and discounted — use proxies, not hallucinated figures |
| Reporting stale data without flagging vintage | BLS/Census lag 12-24 months; in hyper-growth sectors this is functionally useless |
| Presenting a static number instead of an equation | Investors want to see the variables and test them, not trust a single output |
| Using "Labor Replacement" for B2C markets | Consumer category creation is driven by attention and behavior, not efficiency savings |

---

## Search Strategy Rules

1. **Government first**: BLS, Census, BEA for population/wage floor (highest trust)
2. **SEC second**: 10-K revenue segments ground the "what exists" ceiling
3. **Analysts third**: Gartner/GVR/IDC for framing — always tag `Bias: Vendor-Inflation`
4. **Trace every citation**: Find original source behind Forbes/TechCrunch numbers
5. **Domain targeting**: `site:bls.gov`, `site:census.gov`, `site:sec.gov`, `site:bea.gov`
6. **Recency**: Flag sources >24 months. In hyper-growth sectors, flag >12 months
7. **Depth on unknowns**: Run 2-3 follow-up searches before accepting `[UNKNOWN]`
8. **Never fabricate**: If not found, mark `[UNKNOWN]` — do not estimate or hallucinate

---

## Example Invocations

```
User: "market size for AI code review tools"
-> Phase 1: BLS developer count, SEC filings for GitHub/GitLab revenue segments
-> Phase 2: Bottom-up (developers x ACV) capped by top-down (global DevTools spend)
-> Phase 3: Value chain (cloud, IDE marketplace cuts), Fragile Variable (ACV assumption)

User: "TAM for a new B2C social fitness app"
-> Novel Market: B2C "Share of Time" engine — fitness app ARPU x target demographic
-> Revenue Ceiling: Peloton, Strava, MyFitnessPal 10-K segments
-> "Why Now": wearable penetration, post-COVID fitness behavior shift

User: "how big is the compliance automation market"
-> Established market: Analyst reports (with vendor-inflation tag) + SEC filings
-> Bottom-up: Compliance officers (BLS) x tool spend per seat
-> "Do Nothing" discount: heavy — most firms still use manual/Excel processes

User: "size the market for autonomous delivery robots — this category barely exists"
-> Novel Market: B2B "Cost of Status Quo" — last-mile delivery cost x volume
-> Adjacent: food delivery TAM as ceiling, logistics labor costs from BLS
-> Fragile Variable: regulatory approval timeline for sidewalk operation
```

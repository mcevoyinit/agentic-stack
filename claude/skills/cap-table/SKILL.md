---
name: cap-table
description: |
  Deep-research cap table reconstruction for any company (public or private).
  Triangulates ownership from SEC filings, funding rounds, tender offers, proxy
  statements, press releases, and secondary market data. Produces a structured
  ownership breakdown with confidence levels and dilution timeline.
  Trigger: "cap table", "cap-table", "ownership breakdown", "who owns",
  "shareholder structure", "equity structure", "ownership structure".
  DO NOT activate for: Simple valuation lookups (use WebSearch), stock price
  checks, or general company profiles.
---

# Cap Table Reconstruction Skill

> Private company cap tables are never fully public. The skill of cap table
> research is triangulation — piecing together ownership from funding rounds,
> SEC filings, press leaks, and mathematical inference. Every number gets a
> confidence tag.

## Activation

```
ACTIVATE when user says:
  "cap table", "cap-table", "ownership breakdown", "who owns [company]",
  "shareholder structure", "equity structure", "ownership structure",
  "investor stakes in [company]"

DO NOT activate for:
  - Simple "what is [company] worth?" → use WebSearch directly
  - Stock price lookups → use WebSearch
  - General company overview → use /software-estate or WebSearch
```

## Input

The user provides a **company name** (required) and optionally:
- A specific date/round to snapshot ("as of Series C")
- Whether to include estimated ESOP/option pool
- Whether to focus on founder vs. institutional breakdown

If no company name is clear, ask: "Which company's cap table should I research?"

---

## Research Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAP TABLE RECONSTRUCTION                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: CLASSIFY             Determine company type & data    │
│  ──────────────────            availability                     │
│                                                                 │
│  Phase 2: FUNDING HISTORY      Every round, amount, valuation,  │
│  ─────────────────────         lead investor, date              │
│                                                                 │
│  Phase 3: OWNERSHIP STAKES     Named shareholders + percentages │
│  ────────────────────────      from filings, press, estimates   │
│                                                                 │
│  Phase 4: FOUNDER TRACKING     Founder dilution across rounds   │
│  ────────────────────────                                       │
│                                                                 │
│  Phase 5: SECONDARY MARKET     Tender offers, 409A, secondary   │
│  ────────────────────────      transactions, share buybacks     │
│                                                                 │
│  Phase 6: TRIANGULATE          Cross-reference all sources,     │
│  ─────────────────────         resolve conflicts, assign        │
│                                confidence levels                │
│                                                                 │
│  Phase 7: SYNTHESIZE           Final cap table + dilution       │
│  ────────────────────          timeline + commentary            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: CLASSIFY

Determine the company type to route research strategy.

**Decision tree:**
1. Is it publicly traded? → SEC EDGAR is primary source (10-K, DEF 14A proxy)
2. Is it a late-stage private company ($1B+ valuation)? → Press + Crunchbase + PitchBook + secondary market
3. Is it an early-stage startup? → Crunchbase + AngelList + press only
4. Is it acquired/defunct? → Historical filings + acquisition press

**WebSearch queries (run in parallel):**
```
"[COMPANY] SEC filing 10-K proxy statement"
"[COMPANY] IPO S-1 filing"
"[COMPANY] crunchbase funding rounds"
"[COMPANY] private OR public company valuation 2025 2026"
```

**Route:**
- If SEC filings exist → Phase 2A (public path)
- If no filings → Phase 2B (private path)

---

## Phase 2: FUNDING HISTORY

### Goal
Build the complete funding round timeline. This is the backbone of cap table reconstruction.

### Phase 2A: Public Company Path

**WebSearch queries (sequential, quote-exact):**
```
"[COMPANY] S-1 filing principal stockholders"
"[COMPANY] DEF 14A proxy statement beneficial ownership"
"[COMPANY] 10-K annual report shares outstanding"
site:sec.gov "[COMPANY]" "beneficial ownership"
```

**WebFetch targets:**
- SEC EDGAR search: `https://efts.sec.gov/LATEST/search-index?q=%22[COMPANY]%22&dateRange=custom&startdt=2020-01-01&enddt=2026-12-31&forms=DEF+14A,S-1,10-K`
- If found, fetch the most recent DEF 14A (proxy) for beneficial ownership table

### Phase 2B: Private Company Path

**WebSearch queries (run ALL, in parallel where possible):**
```
"[COMPANY] seed round funding amount investor"
"[COMPANY] Series A funding valuation lead investor"
"[COMPANY] Series B funding valuation lead investor"
"[COMPANY] Series C funding valuation lead investor"
"[COMPANY] Series D funding valuation lead investor"
"[COMPANY] total funding raised investors"
"[COMPANY] funding history all rounds crunchbase"
"[COMPANY] latest valuation 2025 2026"
"[COMPANY] tender offer secondary transaction share sale"
```

**WebFetch targets (try in order):**
```
https://www.crunchbase.com/organization/[company-slug]
https://tracxn.com/d/companies/[company-slug]
https://pitchbook.com/profiles/company/[company-slug]  (often paywalled)
```

**Extract into this table:**

| Round | Date | Amount Raised | Pre-Money Val | Post-Money Val | Lead Investor(s) | Key Participants | Source | Confidence |
|-------|------|---------------|---------------|----------------|-------------------|------------------|--------|------------|

**Rules:**
- Every cell gets a source citation
- If amount and valuation are known, compute implied ownership sold: `amount / post-money`
- If only amount is known, mark valuation as `[UNKNOWN]`
- Run additional searches for any round where data is sparse:
  ```
  "[COMPANY] [ROUND] [YEAR] million valuation"
  "[LEAD INVESTOR] investment [COMPANY]"
  ```

---

## Phase 3: OWNERSHIP STAKES

### Goal
Find named shareholders and their percentage ownership.

**WebSearch queries (run in parallel):**
```
"[COMPANY] ownership percentage breakdown shareholders"
"[COMPANY] founder ownership stake percent"
"[COMPANY] [FOUNDER NAME] owns percent shares"
"[COMPANY] largest shareholders investors percentage"
"[COMPANY] employee stock option pool ESOP percentage"
"[COMPANY] beneficial ownership table"
site:bloomberg.com "[FOUNDER NAME]" "[COMPANY]" "stake"
site:forbes.com "[FOUNDER NAME]" "[COMPANY]" "owns" OR "stake" OR "percent"
```

**For public companies, additionally:**
```
"[COMPANY] institutional ownership 13F filing"
"[COMPANY] insider ownership percentage"
site:sec.gov "[COMPANY]" "Schedule 13D" OR "Schedule 13G"
```

**Cross-reference with Bloomberg Billionaires / Forbes if founders are billionaires:**
```
"[FOUNDER NAME] net worth [COMPANY] stake"
"[FOUNDER NAME] bloomberg billionaires [COMPANY]"
```

**Reverse-engineer from net worth (when direct % unavailable):**
```
If founder net worth ≈ $X billion (from Forbes/Bloomberg)
And company valuation ≈ $Y billion
Then estimated stake ≈ X / Y (adjusted for other assets)
Mark as [INFERRED from net worth] with LOW confidence
```

---

## Phase 4: FOUNDER TRACKING

### Goal
Trace founder dilution across every funding round.

**Method:**
1. Start with assumed 100% founder ownership at incorporation
2. For each round, if ownership sold is known (`amount / post-money`), subtract from founder pool
3. Subtract estimated ESOP (typically 10-20% by Series B)
4. Cross-check against any reported founder percentages

**WebSearch queries:**
```
"[FOUNDER NAME] dilution [COMPANY] ownership over time"
"[COMPANY] founder retained ownership percentage"
"[COMPANY] option pool size employee equity"
```

**Dilution model (when computing from rounds):**

```
Round N founder ownership = Previous ownership × (1 - dilution_N)
Where dilution_N = amount_raised_N / post_money_valuation_N

Typical ESOP carve-outs:
  Seed:     10-15% option pool created
  Series A: Refreshed to 10-15%
  Series B: Refreshed to 10-12%
  Series C+: Refreshed to 8-10%
```

Mark ALL computed values as `[COMPUTED]` with methodology noted.

---

## Phase 5: SECONDARY MARKET & SPECIAL EVENTS

### Goal
Capture share sales, buybacks, tender offers, and other cap table events.

**WebSearch queries:**
```
"[COMPANY] tender offer employees shares 2024 2025 2026"
"[COMPANY] secondary market share sale"
"[COMPANY] share buyback repurchase"
"[COMPANY] down round valuation cut"
"[COMPANY] stock split reverse split"
"[COMPANY] SPAC merger acquisition"
"[COMPANY] 409A valuation"
"[COMPANY] employee liquidity event"
```

**Note any:**
- Anti-dilution protections triggered (ratchets)
- Liquidation preference stacking
- Dual-class share structures
- Voting vs. economic ownership splits

---

## Phase 6: TRIANGULATE

### Goal
Cross-reference all sources. Resolve conflicts. Assign confidence levels.

**Confidence framework:**

| Level | Criteria | Tag |
|-------|----------|-----|
| **HIGH** | From SEC filing, official company announcement, or confirmed by 3+ independent sources | `[HIGH]` |
| **MEDIUM** | From 2 independent press sources, or 1 credible source (TechCrunch, Bloomberg, WSJ) | `[MEDIUM]` |
| **LOW** | Single source, blog, or analyst estimate | `[LOW]` |
| **INFERRED** | Computed from other known values (e.g., dilution math, net worth reverse-engineering) | `[INFERRED]` |
| **UNKNOWN** | No data found after exhaustive search | `[UNKNOWN]` |

**Conflict resolution rules:**
1. SEC filings > press reports > analyst estimates > blog posts
2. More recent source > older source (for same data point)
3. If two credible sources conflict, report BOTH with a note
4. Never average conflicting percentages — present the range

---

## Phase 7: SYNTHESIZE — Final Output

### Output Format (MANDATORY)

Produce ALL of the following sections:

---

#### 1. Company Overview

```
Company:        [NAME]
Status:         [Public (TICKER) | Private | Acquired by X]
Latest Valuation: $[X]B ([DATE], [SOURCE])
Total Raised:   $[X]B across [N] rounds
Founded:        [YEAR]
Founders:       [NAMES]
HQ:             [LOCATION]
```

#### 2. Cap Table — Current Estimated Ownership

| Shareholder | Type | Est. Stake | Confidence | Source |
|---|---|---|---|---|
| [Founder 1] | Founder | X% | [HIGH/MED/LOW/INFERRED] | [Source] |
| [Founder 2] | Founder | X% | ... | ... |
| [VC Firm 1] | Institutional | X% | ... | ... |
| [VC Firm 2] | Institutional | X% | ... | ... |
| Employee Pool (ESOP) | Option Pool | X% | [INFERRED] | Typical for stage |
| Other / Unattributed | — | X% | — | Remainder |
| **Total** | | **100%** | | |

**Rules:**
- Always sum to 100%. Use "Other / Unattributed" as the balancing line.
- If total known stakes exceed 100%, flag as `[CONFLICT]` and explain.
- Sort by stake size descending.

#### 3. Funding Round History

| # | Round | Date | Raised | Pre-$ Val | Post-$ Val | Lead Investor | Implied Dilution | Source |
|---|-------|------|--------|-----------|------------|---------------|-----------------|--------|
| 1 | Seed | ... | ... | ... | ... | ... | X% | ... |
| 2 | Series A | ... | ... | ... | ... | ... | X% | ... |
| ... | | | | | | | | |

#### 4. Dilution Waterfall (Founder Perspective)

| Event | Founder Ownership After | Dilution This Round | Cumulative Dilution |
|-------|------------------------|--------------------|--------------------|
| Founding | 100% | — | 0% |
| ESOP Creation | ~85% | ~15% | 15% |
| Seed | ~X% | ~Y% | ~Z% |
| Series A | ~X% | ~Y% | ~Z% |
| ... | | | |

#### 5. Secondary Market & Special Events

| Date | Event | Details | Impact on Cap Table |
|------|-------|---------|-------------------|
| ... | Tender offer | ... | ... |
| ... | Share buyback | ... | ... |

*If none found, state: "No secondary transactions identified."*

#### 6. Notable Cap Table Features

Flag any of the following if detected:
- [ ] Dual-class share structure (voting vs. economic)
- [ ] Super-voting shares (founder control)
- [ ] Liquidation preferences (participating vs. non-participating)
- [ ] Anti-dilution provisions (full ratchet vs. weighted average)
- [ ] Right of first refusal (ROFR) on secondary sales
- [ ] IPO lock-up provisions
- [ ] Pay-to-play clauses

#### 7. Data Gaps & Caveats

List everything you could NOT find, and what additional sources might resolve it:
```
- [GAP]: Exact Sequoia stake unknown. Would need Series A term sheet or proxy filing.
- [GAP]: ESOP size estimated at industry standard. Actual could be 8-20%.
- [CAVEAT]: All private company ownership is estimated. True cap table is confidential.
```

#### 8. Sources

Full list of every URL consulted, grouped by type:
```
SEC Filings:
  - [url1]

Press / News:
  - [url2]
  - [url3]

Data Providers:
  - [url4]

Analyst / Blog:
  - [url5]
```

---

## Research Execution Rules

### Search Strategy
1. **Breadth first**: Run all Phase 2 queries in parallel to establish baseline
2. **Depth on gaps**: For any cell marked `[UNKNOWN]`, run 2-3 targeted follow-up searches
3. **Source diversity**: Never rely on a single source. Triangulate every key number
4. **Recency bias**: Prefer 2025-2026 sources over older ones for current ownership
5. **Domain targeting**: Use `site:` operator for high-signal domains:
   - `site:sec.gov` for filings
   - `site:techcrunch.com` for funding rounds
   - `site:bloomberg.com` for ownership/net worth
   - `site:wsj.com` for funding/valuation
   - `site:forbes.com` for founder wealth/stakes
   - `site:crunchbase.com` for round history

### WebFetch Strategy
- Fetch full articles from TechCrunch, Bloomberg, WSJ for exact numbers
- Fetch SEC filings (EDGAR) for beneficial ownership tables
- Fetch Crunchbase/Tracxn company pages for round summaries
- If a page is paywalled, note it and try alternative sources

### Quality Gates
- [ ] Every percentage has a source or is marked `[INFERRED]`
- [ ] Every round has at least: date, amount, and lead investor
- [ ] Founder dilution math is internally consistent
- [ ] Total ownership sums to 100% (with balancing line)
- [ ] At least 3 independent sources consulted
- [ ] All data gaps explicitly listed

### Anti-Patterns (DO NOT)

| Anti-Pattern | Why It Fails |
|---|---|
| Guessing percentages without sources | Creates false confidence in fabricated data |
| Averaging conflicting numbers | Destroys signal — report the range instead |
| Ignoring ESOP / option pool | Understates dilution by 10-20% |
| Using outdated round data for current ownership | Cap tables change with every transaction |
| Treating all shares as equal | Misses dual-class, preferences, voting rights |
| Stopping after 2 searches | Private cap tables require 8-15+ searches to triangulate |
| Presenting estimates as facts | Always tag confidence level |

---

## Example Invocations

```
User: "cap table for Stripe"
→ Full 7-section output, heavy on Phase 2B (private), Phase 5 (tender offers)

User: "who owns Databricks"
→ Activate cap-table skill, focus on institutional vs. founder split

User: "ownership breakdown for Tesla"
→ Phase 2A (public), fetch DEF 14A from SEC EDGAR, 13F institutional ownership

User: "cap-table Anthropic as of Series D"
→ Snapshot ownership at specific round, show dilution waterfall up to that point
```

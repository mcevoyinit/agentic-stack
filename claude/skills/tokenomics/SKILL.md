---
name: tokenomics
description: |
  Deep-research token economics reconstruction for any crypto protocol.
  Maps stated intent against data consensus to expose contradictions,
  liquidity realities, centralization risks, and true treasury composition.
  8-phase semantic synthesis with 5-tier confidence tagging.
  Trigger: "tokenomics", "token economics", "token distribution",
  "emission schedule", "vesting schedule", "token utility", "staking mechanics".
  DO NOT activate for: Simple token price lookups, portfolio tracking,
  or trading signals.
---

# Tokenomics Research Skill

> Tokenomics is where marketing meets math. The agent's job is not to read
> smart contracts (it can't) — it's to map the protocol's stated intent,
> verify structural consensus across aggregators, and audit for logical
> contradictions, liquidity realities, and centralization vectors.

## Activation

```
ACTIVATE when user says:
  "tokenomics", "token economics", "token distribution", "emission schedule",
  "vesting schedule", "token utility", "staking mechanics", "governance token",
  "[protocol] token", "tokenomics of [protocol]"

DO NOT activate for:
  - Token price lookups → use WebSearch directly
  - Portfolio tracking → not a research skill
  - Trading signals / buy-sell advice → refuse
  - General protocol overview → use /software-estate
```

## Input

User provides a **protocol or token name** (required) and optionally:
- Snapshot date ("as of mainnet launch")
- Focus area ("just the vesting and unlocks")
- Comparison targets ("compare vs Ethereum and Solana")

If no protocol is clear, ask: "Which protocol's tokenomics should I research?"

---

## Core Design Principle

**Semantic Consistency Auditor, NOT On-Chain Inspector.**

Claude Code is a text-prediction engine, not a blockchain node. It cannot:
- Read raw Solidity and deduce emission formulas
- Query on-chain state or RPC endpoints
- Bypass JavaScript-gated dashboards (Dune, Token Terminal)

It CAN:
- Perfectly map a protocol's stated rules from documentation
- Cross-reference claims against multiple aggregator summaries
- Detect logical contradictions across the protocol's own literature
- Flag structural centralization risks from text descriptions
- Synthesize complex multi-source findings into actionable tables

---

## Confidence Tagging System (5-Tier)

| Tag | Criteria | When to Use |
|-----|----------|-------------|
| `[VERIFIED_INTENT]` | Explicitly stated in official, current documentation (docs site, whitepaper, blog) | Supply caps, stated allocations, described governance model |
| `[CONSENSUS_DATA]` | Matched across 2+ reputable third-party aggregators | Circulating supply, TVL, market cap — cross-checked CoinGecko + DefiLlama |
| `[CONTRADICTION]` | Conflicting data between official docs and aggregators, or within docs themselves | Whitepaper says hard cap but GitBook mentions tail emission |
| `[UNVERIFIABLE_MATH]` | Derived metric requiring multi-step arithmetic — flagged for user verification | "Effective inflation = stated + unlock dilution" — user should verify |
| `[UNKNOWN]` | Data not reliably found after 3+ targeted searches | Specific investor allocations for private rounds |

**Critical rule**: Never assign `[CONSENSUS_DATA]` based on a single source. If only one aggregator reports a number, downgrade to `[VERIFIED_INTENT]` if it matches docs, or `[UNKNOWN]` if it doesn't.

---

## Research Architecture (8 Phases)

```
┌──────────────────────────────────────────────────────────────────┐
│                    TOKENOMICS RECONSTRUCTION                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: BASELINE OF INTENT     Map stated rules from docs      │
│  ──────────────────────────                                      │
│                                                                  │
│  Phase 2: MACRO SUPPLY           Total/max/circulating + alloc   │
│  ─────────────────────           buckets with semantic audit     │
│                                                                  │
│  Phase 3: TIME VECTOR            Vesting, cliffs, unlock         │
│  ────────────────────            schedule, inflation rate        │
│                                                                  │
│  Phase 4: LIQUIDITY REALITY      DEX depth, slippage, CEX        │
│  ────────────────────────        listings, market making         │
│                                                                  │
│  Phase 5: BUSINESS MODEL         Fee generation, MEV, burns,     │
│  ────────────────────────        value accrual, real yield       │
│                                                                  │
│  Phase 6: CONTROL VECTORS        Upgradability, multisig,        │
│  ─────────────────────           governance, delegation          │
│                                                                  │
│  Phase 7: TREASURY REALITY       Runway with stablecoin vs       │
│  ─────────────────────           native token separation         │
│                                                                  │
│  Phase 8: SYNTHESIS              Tables, contradictions,         │
│  ────────────────────            comparisons, risk matrix        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: BASELINE OF INTENT

### Goal
Map the protocol's stated tokenomic rules from official documentation. This is the canonical "what it's supposed to do" baseline that all subsequent phases audit against.

### WebSearch Queries
```
"[PROTOCOL]" tokenomics site:docs.[PROTOCOL].com OR site:[PROTOCOL].xyz
"[PROTOCOL]" whitepaper tokenomics OR "token economics"
"[PROTOCOL]" "token distribution" OR "allocation" official
"[TOKEN]" tokenomics blog announcement
"[PROTOCOL]" litepaper OR "economic paper" OR "token paper"
```

### WebFetch Targets
- Official docs tokenomics page (usually `docs.[protocol].com/tokenomics`)
- Whitepaper / litepaper PDF or page
- Foundation blog post announcing token launch

### Extract
- Token name, ticker, chain(s) deployed on
- Stated total supply / max supply
- High-level allocation categories and percentages
- Core utility claims (governance, gas, staking, payment, etc.)
- Any stated emission/inflation model
- Genesis date / TGE (Token Generation Event) date

**Tag everything from this phase as `[VERIFIED_INTENT]`.**

---

## Phase 2: MACRO SUPPLY & SEMANTIC DISTRIBUTION

### Goal
Map token allocation buckets and apply the **semantic audit** — flag misleading category names.

### WebSearch Queries
```
"[TOKEN]" circulating supply total supply site:coingecko.com
"[TOKEN]" supply distribution site:messari.io
"[TOKEN]" allocation breakdown investors team community
"[PROTOCOL]" "token allocation" pie chart OR breakdown
"[TOKEN]" max supply cap inflation deflation
```

### Semantic Audit Rules (MANDATORY)

| Stated Category | Audit Question | Flag If... |
|---|---|---|
| "Community" / "Ecosystem Fund" | Is there a programmatic vesting schedule? Is it governed by on-chain vote? | No vesting + no on-chain governance → flag as `⚠ TEAM-CONTROLLED` |
| "Foundation" | Who controls the multisig? How many signers? | <5 signers or all core team → flag as `⚠ CENTRALIZED CONTROL` |
| "Advisors" | What's the vesting? Who are the advisors? | No public advisor list + short vesting → flag as `⚠ INSIDER ALLOCATION` |
| "Treasury" / "Reserve" | Governed by DAO or team? | Team-controlled → flag as `⚠ DISCRETIONARY` |
| "Staking Rewards" / "Mining" | Is this inflationary new issuance? | Yes → flag as `⚠ DILUTIVE EMISSION` |

### Output Table

| Category | Stated % | Amount | Lock Status | Semantic Audit Flag | Confidence |
|----------|----------|--------|-------------|--------------------|-----------|
| Team | X% | X tokens | Vesting details | — | [tag] |
| Investors | X% | X tokens | Vesting details | — | [tag] |
| Community/Ecosystem | X% | X tokens | Lock details | ⚠ flag if applicable | [tag] |
| Foundation/Treasury | X% | X tokens | Governance model | ⚠ flag if applicable | [tag] |
| Staking/Mining | X% | X tokens | Emission type | ⚠ DILUTIVE if inflationary | [tag] |
| Public Sale | X% | X tokens | — | — | [tag] |
| Other | X% | X tokens | — | — | [tag] |
| **Total** | **100%** | **X tokens** | | | |

---

## Phase 3: THE TIME VECTOR

### Goal
Map vesting schedules, unlock cliffs, and the forward emission calendar.

### WebSearch Queries
```
"[TOKEN]" vesting schedule unlock cliff
"[PROTOCOL]" "token unlock" 2025 OR 2026 OR 2027
"[TOKEN]" unlock calendar site:token.unlocks.app OR site:vestlab.io
"[TOKEN]" emission schedule inflation rate annual
"[PROTOCOL]" "investor unlock" OR "team unlock" date
```

### Output Table — Vesting Schedule

| Stakeholder | Allocation | Cliff | Vesting Period | Unlock Start | Full Unlock | Confidence |
|---|---|---|---|---|---|---|
| Team | X% | 12 months | 36-month linear | Date | Date | [tag] |
| Seed Investors | X% | 6 months | 24-month linear | Date | Date | [tag] |
| Series A | X% | ... | ... | ... | ... | [tag] |
| ... | | | | | | |

### Output Table — Upcoming Unlock Events (Next 12 Months)

| Date | Stakeholder | Tokens Unlocking | % of Circulating | Impact Assessment | Confidence |
|---|---|---|---|---|---|
| YYYY-MM | ... | X tokens | X% | HIGH/MEDIUM/LOW sell pressure | [tag] |

### Critical Computation (flagged)
```
⚠ [UNVERIFIABLE_MATH] — User should independently verify:
Monthly new supply entering circulation = Staking emissions + Vesting unlocks
Effective annual inflation vs circulating = (12-month new supply / current circulating) × 100
```

---

## Phase 4: LIQUIDITY REALITY

### Goal
Ground the tokenomics in actual market depth. A perfect distribution is irrelevant if liquidity is $50K.

### WebSearch Queries
```
"[TOKEN]" liquidity TVL site:defillama.com
"[TOKEN]" trading volume 24h site:coingecko.com OR site:coinmarketcap.com
"[TOKEN]" DEX liquidity pool depth
"[TOKEN]" exchange listings CEX
"[PROTOCOL]" market maker partnership OR "liquidity provision"
"[TOKEN]" slippage "$100k" OR "$1M" trade
```

### Output Table

| Metric | Value | Source | Confidence |
|--------|-------|--------|------------|
| 24h Trading Volume | $X | CoinGecko/CMC | [CONSENSUS_DATA] |
| Largest DEX Pool | Pool name, $X TVL | DefiLlama | [tag] |
| CEX Listings | Exchange names | CoinGecko | [tag] |
| Est. Slippage ($100K sell) | X% | DEX aggregator data | [tag] |
| Market Maker | Name if known | Press/announcements | [tag] |
| Volume/MCap Ratio | X% | Computed | [UNVERIFIABLE_MATH] |

**Flag**: If 24h volume < $1M or largest pool TVL < $500K, mark as `⚠ ILLIQUID — tokenomics may be theoretical`

---

## Phase 5: BUSINESS MODEL (Network Bootstrapping vs. Extraction)

### Goal
Evaluate whether the token captures real economic value or just redistributes inflation.

### WebSearch Queries
```
"[PROTOCOL]" revenue fees site:tokenterminal.com OR site:defillama.com
"[PROTOCOL]" fee structure gas cost
"[TOKEN]" burn mechanism buyback deflation
"[PROTOCOL]" MEV extraction OR "MEV protection"
"[PROTOCOL]" "real yield" OR "protocol revenue"
"[TOKEN]" staking APY yield source
```

### Dual-Frame Analysis (MANDATORY)

**Frame A — Value Extraction Lens:**
- What % of staking yield comes from new token emission (dilutive)?
- What % comes from protocol fees (real yield)?
- Real Yield = Staking APY - Network Inflation Rate
- If Real Yield < 0 → `⚠ YIELD IS PURELY DILUTIVE`

**Frame B — Network Bootstrapping Lens:**
- Is token emission effectively acquiring users/TVL?
- Effective CAC = (Monthly emission × token price) / Monthly new users
- Is the network building permanent switching costs / moats?
- Would the network collapse if emissions stopped?

### Output Table

| Revenue Metric | Value | Source | Confidence |
|---|---|---|---|
| Annual Protocol Revenue | $X | Token Terminal / DefiLlama | [tag] |
| Fee Distribution | X% to stakers, X% burned, X% treasury | Docs | [VERIFIED_INTENT] |
| Staking APY (Nominal) | X% | Aggregator | [tag] |
| Network Inflation Rate | X% | Computed | [UNVERIFIABLE_MATH] |
| Real Yield (APY - Inflation) | X% | Computed | [UNVERIFIABLE_MATH] |
| Burn Rate (if applicable) | X tokens/month | On-chain aggregator | [tag] |

---

## Phase 6: CONTROL VECTORS

### Goal
Determine who actually controls the protocol — governance theater vs. real power.

### WebSearch Queries
```
"[PROTOCOL]" governance model voting on-chain
"[PROTOCOL]" "multisig" OR "proxy" OR "upgradable" site:github.com
"[PROTOCOL]" governance proposal quorum participation
"[TOKEN]" delegation concentration top holders
"[PROTOCOL]" "admin key" OR "owner" OR "pause" contract
"[PROTOCOL]" governance forum recent proposals passed
```

### Control Vector Checklist

| Control Vector | Status | Risk Level | Confidence |
|---|---|---|---|
| Token contract upgradable (proxy)? | Yes/No | CRITICAL if yes | [tag] |
| Multisig threshold & signers | X-of-Y, identities | HIGH if <5 or all team | [tag] |
| Admin/pause functionality | Yes/No | HIGH if exists | [tag] |
| Top 10 holder concentration | X% of supply | Context-dependent | [tag] |
| Voter participation rate | X% of supply votes | LOW participation = risk | [tag] |
| Delegation monopoly | Top 3 delegates hold X% | HIGH if >50% | [tag] |
| Timelock on governance | X hours/days | Shorter = riskier | [tag] |

**Critical flag**: If token contract is an upgradable proxy controlled by a small multisig, mark: `⚠ TOKENOMICS MUTABLE — Core team can change rules via proxy upgrade`

---

## Phase 7: TREASURY REALITY

### Goal
Calculate real runway by separating stablecoins from native token holdings.

### WebSearch Queries
```
"[PROTOCOL]" treasury balance OR holdings
"[PROTOCOL]" DAO treasury site:deepdao.io OR site:defillama.com
"[PROTOCOL]" foundation treasury diversification
"[PROTOCOL]" treasury spending budget proposal
"[PROTOCOL]" grant program budget annual
```

### Output Table — Treasury Composition (MANDATORY SEPARATION)

| Asset Type | Holdings | USD Value | % of Treasury | Confidence |
|---|---|---|---|---|
| Stablecoins (USDC, USDT, DAI) | X tokens | $X | X% | [tag] |
| Major Crypto (ETH, BTC) | X tokens | $X | X% | [tag] |
| Native Token ([TOKEN]) | X tokens | $X | X% | [tag] |
| Other Tokens | X tokens | $X | X% | [tag] |
| **Total (Face Value)** | | **$X** | **100%** | |
| **Total (Excluding Native Token)** | | **$X** | | |

### Runway Calculation

```
⚠ [UNVERIFIABLE_MATH] — User should independently verify:
Monthly burn rate = Known team size × avg. crypto salary estimate + known grants/spending
Real runway = (Stablecoin + Major Crypto holdings) / Monthly burn rate
Face-value runway = Total treasury / Monthly burn rate

⚠ If Native Token > 80% of treasury → "TREASURY ILLUSION — real runway is X months, not Y"
```

---

## Phase 8: SYNTHESIS

### 8A. Protocol Overview

```
Protocol:       [NAME]
Token:          [TICKER] on [CHAIN(S)]
Status:         [Mainnet / Testnet / Pre-launch]
TGE Date:       [DATE]
Total Supply:   [X] tokens ([Hard cap / Inflationary])
Circulating:    [X] tokens ([X]% of total)
Market Cap:     $[X] ([Source], [Date])
FDV:            $[X]
Category:       [L1 / L2 / DeFi / Infra / etc.]
```

### 8B. Distribution Table (with semantic flags)
*From Phase 2*

### 8C. Vesting & Unlock Calendar
*From Phase 3*

### 8D. Liquidity Assessment
*From Phase 4*

### 8E. Revenue & Yield Reality
*From Phase 5*

### 8F. Control & Governance Assessment
*From Phase 6*

### 8G. Treasury Reality
*From Phase 7*

### 8H. Idiosyncratic Mechanics (MANDATORY)

Capture ANY novel tokenomic mechanisms that don't fit standard tables:

| Mechanism | Description | Impact | Comparable To | Confidence |
|---|---|---|---|---|
| e.g., veTokenomics | Vote-escrow locking for governance weight | Reduces circulating supply, concentrates governance | Curve (veCRV) | [tag] |
| e.g., Restaking | LST collateral reused for additional security | Leveraged staking, systemic risk | EigenLayer | [tag] |
| e.g., Points-to-Token | Off-chain points converted to tokens at TGE | Pre-TGE speculation, unknown dilution | Blast, various | [tag] |

### 8I. Logical Contradictions Found (MANDATORY)

| Contradiction | Source A | Source B | Severity | Resolution |
|---|---|---|---|---|
| e.g., Whitepaper says 1B hard cap, GitBook says tail emission | Whitepaper v1 p.12 | docs.protocol.com/economics | HIGH | Needs clarification from team |

*If no contradictions found, state: "No contradictions detected across [N] sources consulted."*

### 8J. Risk Matrix

| Risk | Severity | Likelihood | Evidence | Confidence |
|---|---|---|---|---|
| Insider concentration | HIGH/MED/LOW | HIGH/MED/LOW | Description | [tag] |
| Upcoming unlock cliff | ... | ... | ... | [tag] |
| Treasury illusion | ... | ... | ... | [tag] |
| Governance capture | ... | ... | ... | [tag] |
| Contract upgradability | ... | ... | ... | [tag] |
| Liquidity crisis | ... | ... | ... | [tag] |
| Inflationary yield | ... | ... | ... | [tag] |

### 8K. Comparative Analysis (if requested)

| Metric | [PROTOCOL] | Comp 1 | Comp 2 | Comp 3 |
|--------|-----------|--------|--------|--------|
| Total Supply | X | X | X | X |
| Inflation Rate | X% | X% | X% | X% |
| Insider Allocation | X% | X% | X% | X% |
| Real Yield | X% | X% | X% | X% |
| Treasury Runway | X months | X months | X months | X months |
| Governance Participation | X% | X% | X% | X% |

### 8L. Data Gaps & Caveats

```
- [GAP]: Specific Series A investor allocation not publicly disclosed
- [GAP]: Treasury composition inferred from DefiLlama, not verified on-chain
- [CAVEAT]: All derived math flagged as [UNVERIFIABLE_MATH] — user should verify
- [CAVEAT]: Tokenomics are dynamic — governance vote could change parameters
- [STALE]: Data as of [DATE] — check for recent governance proposals
```

### 8M. Sources

```
Official Documentation:
  - [url1]

Aggregators (Cross-Referenced):
  - [url2]
  - [url3]

Press / Analysis:
  - [url4]

Governance / Community:
  - [url5]
```

---

## Search Strategy Rules

1. **Docs first**: Establish baseline of intent before checking aggregators
2. **Cross-reference everything**: Never trust a single aggregator. CoinGecko + DefiLlama minimum
3. **Domain targeting**: Use `site:` for high-signal domains:
   - `site:coingecko.com` — supply, market data
   - `site:defillama.com` — TVL, treasury, yields
   - `site:messari.io` — research reports, governance
   - `site:tokenterminal.com` — revenue, fees (often summarized in press)
   - `site:github.com` — contract upgradability, multisig configs
   - `site:deepdao.io` — DAO treasury, governance participation
4. **Recency**: Prefer 2025-2026 data. Tokenomics change — check for recent parameter votes
5. **Depth on gaps**: For any `[UNKNOWN]` cell, run 2-3 targeted follow-up searches
6. **Never fabricate numbers**: If a metric isn't found, mark `[UNKNOWN]`, don't estimate

## Anti-Patterns (DO NOT)

| Anti-Pattern | Why It Fails |
|---|---|
| Reading raw Solidity to derive emissions | LLMs hallucinate contract logic — use documented rules instead |
| Treating governance forums as ground truth | Can't distinguish passed vs. failed proposals |
| Accepting "Community" allocation at face value | Often team-controlled without vesting — always audit |
| Reporting nominal APY without inflation context | 20% APY with 25% inflation = -5% real yield |
| Using face-value treasury for runway | 90% native token treasury = mirage |
| Performing multi-step arithmetic without flagging | Math cascades amplify errors — always tag [UNVERIFIABLE_MATH] |
| Ignoring liquidity depth | Perfect tokenomics with $50K liquidity = theoretical |
| Treating tokenomics as static | One governance vote can change everything — timestamp all findings |

---

## Example Invocations

```
User: "tokenomics of Arbitrum"
→ Full 8-phase + 12-section output, heavy on Phase 1 (new L1, docs-heavy)

User: "Ethereum tokenomics vs Solana"
→ Phases 1-8 for both, plus Section 8K comparative table

User: "what are the vesting unlocks for Arbitrum"
→ Focus on Phase 3, abbreviated other phases

User: "is the Optimism token actually useful"
→ Deep Phase 5 (business model), Phase 6 (governance), demand-side analysis
```

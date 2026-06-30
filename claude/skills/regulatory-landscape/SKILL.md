---
name: regulatory-landscape
description: |
  Deep regulatory environment research for any product, technology, or
  business model across jurisdictions. Maps applicable laws, licensing
  requirements, compliance frameworks, enforcement history, and pending
  legislation. Component-based approach handles intersectional products.
  Outputs actionable compliance roadmaps with time-to-compliance and
  capital estimates, not academic legal memos.
  Trigger: "regulatory landscape", "compliance requirements", "licensing",
  "regulatory risk", "what licenses do I need", "is this legal",
  "regulatory environment for", "compliance roadmap".
  DO NOT activate for: Specific legal advice (consult a lawyer), contract
  review, or simple "what is GDPR" factual questions.
---

# Regulatory Landscape — Operational Cartographer

> The AI is an Operational Cartographer — not a fiduciary risk officer, not
> an academic legal researcher. It maps the terrain neutrally: where the
> hard boundaries are, where the gray zones are, what it costs to comply,
> and how long it takes. The human decides the path.

## Activation

```
ACTIVATE when user says:
  "regulatory landscape", "compliance requirements", "licensing requirements",
  "what licenses do I need", "regulatory risk for", "is this legal",
  "compliance roadmap", "regulatory environment", "regulatory for [product]"

DO NOT activate for:
  - Specific legal advice → always add disclaimer to consult counsel
  - Contract review → out of scope
  - Simple "what is GDPR" → use WebSearch directly
  - Tax advice → out of scope
```

## Input

User provides a **product/business description** (required) and optionally:
- Target jurisdictions ("US only", "US + EU", "global")
- Sector hint ("payments", "healthcare AI", "crypto exchange")
- Stage ("pre-launch", "scaling", "enterprise sales")
- Specific regulatory concern ("do I need an MTL?")

If the product isn't clear, ask: "Describe the product/service and which markets you're targeting."

---

## Critical Disclaimer (ALWAYS OUTPUT)

```
⚠ DISCLAIMER: This analysis is an AI-generated research summary, NOT legal
advice. Regulatory landscapes change rapidly. Consult qualified legal counsel
in each relevant jurisdiction before making compliance decisions. This tool
maps the terrain — your lawyer navigates it.
```

---

## Core Design Principles

### 1. Operational Cartographer, Not Risk Officer
The AI does NOT make go/no-go decisions. It presents:
- What's strictly illegal (hard stop)
- What requires licenses/registration (gateway)
- What's gray area (map the penalty landscape)
- What it costs and how long it takes (business strategy)

### 2. Component-Based Search (Not Siloed Industries)
Products cross regulatory domains. Instead of "If crypto → search crypto laws," decompose the product into functional primitives and search each:

| Primitive | Triggers When Product... | Regulatory Domains |
|---|---|---|
| `[FLOW_OF_FUNDS]` | Moves, holds, or transmits money/value | FinCEN, state MTLs, PSD2, EMI, MiCA |
| `[USER_IDENTITY]` | Collects personal data or KYC | GDPR, CCPA, LGPD, KYC/AML |
| `[DATA_STORAGE]` | Stores sensitive/health/financial data | HIPAA, SOC2, PCI-DSS, data residency |
| `[AUTONOMOUS_LOGIC]` | Uses AI/ML for decisions | EU AI Act, state AI laws, fair lending |
| `[TOKEN_ISSUANCE]` | Issues or facilitates trading of tokens | SEC (Howey), CFTC, MiCA, VASP |
| `[HEALTHCARE]` | Touches patient data or clinical decisions | HIPAA, FDA SaMD, HITECH |
| `[CONTENT]` | Hosts user-generated content | DMCA, DSA, Section 230 |

### 3. Jurisdictional Cascade (Sequential, Not Blended)
Always evaluate in order. Never blend jurisdictions:
```
Level 1: International / Treaty (e.g., FATF, Basel)
Level 2: Federal / National (e.g., SEC, GDPR, MiCA)
Level 3: State / Provincial (e.g., NY BitLicense, CA CCPA, IL BIPA)
Level 4: Shadow Regulation (sponsor bank TPRM, app store policies)
```

For EU: Distinguish **Regulations** (directly applicable: GDPR, MiCA) from **Directives** (require member state implementation: PSD2).

### 4. Temporal Triangulation
Every finding gets a temporal tag:

| Tag | Meaning | Weight |
|-----|---------|--------|
| `[CURRENT_LAW]` | Binding statute or regulation currently in force | Treat as absolute |
| `[AGENCY_GUIDANCE]` | Official agency FAQ, interpretive letter, rulemaking | Treat as law for startups |
| `[NO_ACTION_LETTER]` | Explicit safe harbor from regulator | Highest-signal for boundaries |
| `[ENFORCEMENT_PRECEDENT]` | Past enforcement action (lags 3-5 years) | Directional, not current |
| `[PENDING_LEGISLATION]` | Bill introduced but not passed | Monitor, don't comply yet |
| `[COMMERCIAL_FRAMEWORK]` | Industry standard, not law (SOC2, PCI) | B2B requirement, not legal |

---

## Research Architecture (5 Phases)

```
┌──────────────────────────────────────────────────────────────────┐
│                   REGULATORY CARTOGRAPHY                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: DECOMPOSE           Break product into functional      │
│  ─────────────────────        primitives, identify jurisdictions │
│                                                                  │
│  Phase 2: MAP STATUTES        Current law per jurisdiction       │
│  ─────────────────────        per primitive, cascade order       │
│                                                                  │
│  Phase 3: MAP GATEWAYS        Licenses, registrations, and      │
│  ─────────────────────        commercial frameworks needed       │
│                                                                  │
│  Phase 4: GRAY ZONES          Enforcement history, no-action     │
│  ────────────────────         letters, penalty landscape         │
│                                                                  │
│  Phase 5: SYNTHESIZE          Compliance roadmap with TTC,       │
│  ────────────────────         capital, and prioritization        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: DECOMPOSE

### Goal
Break the product into regulatory primitives and identify target jurisdictions.

### Process
1. Parse the user's product description
2. Map to functional primitives (from table above)
3. Identify target jurisdictions from user input or infer from context
4. Load jurisdiction-specific search routes

### Output

```
Product:        [DESCRIPTION]
Primitives:     [FLOW_OF_FUNDS] [USER_IDENTITY] [AUTONOMOUS_LOGIC] ...
Jurisdictions:  [US Federal] [US-NY] [US-CA] [EU] [UK] ...
Complexity:     [LOW: 1-2 primitives | MEDIUM: 3-4 | HIGH: 5+]
```

---

## Phase 2: MAP STATUTES

### Goal
For each primitive × jurisdiction combination, identify the current binding law.

### WebSearch Query Templates (per primitive)

**[FLOW_OF_FUNDS]:**
```
"money transmission" OR "money transmitter" license requirements [JURISDICTION] site:.gov
"payment services" regulation [JURISDICTION] site:.gov OR site:.europa.eu
FinCEN "money services business" MSB registration requirements
"[JURISDICTION]" "money transmitter license" application requirements
"PSD2" OR "EMI" "electronic money institution" [JURISDICTION]
MiCA "crypto-asset service provider" CASP requirements
```

**[USER_IDENTITY]:**
```
"data protection" OR "privacy" law [JURISDICTION] site:.gov
GDPR "data controller" obligations requirements
CCPA CPRA "business" obligations California
"[JURISDICTION]" "data residency" OR "data localization" requirements
KYC AML "customer due diligence" [JURISDICTION] requirements
```

**[TOKEN_ISSUANCE]:**
```
"securities" "registration" "exemption" [TOKEN_TYPE] site:sec.gov
"Howey test" "investment contract" [PRODUCT_TYPE]
MiCA "crypto-asset" classification requirements
"[JURISDICTION]" "virtual asset service provider" VASP registration
CFTC "digital commodity" OR "digital asset" classification
```

**[AUTONOMOUS_LOGIC]:**
```
"EU AI Act" "high-risk" classification requirements
"[JURISDICTION]" "artificial intelligence" regulation law 2025 2026
"algorithmic" "fairness" OR "transparency" requirements [JURISDICTION]
"automated decision" "right to explanation" [JURISDICTION]
```

**[HEALTHCARE]:**
```
HIPAA "covered entity" "business associate" requirements
FDA "software as a medical device" SaMD classification
"[JURISDICTION]" "telehealth" OR "telemedicine" regulation
"clinical decision support" FDA regulation exemption
```

**[DATA_STORAGE]:**
```
"[JURISDICTION]" "data breach notification" requirements
PCI DSS requirements "cardholder data" compliance
SOC 2 "trust services criteria" requirements
"[JURISDICTION]" "data residency" "server location" requirements
```

### Shadow Regulation Search (MANDATORY for fintech)
```
"sponsor bank" "third party risk management" TPRM requirements
"BaaS" "banking as a service" compliance partner requirements
"[BANK_NAME]" consent order OCC FDIC
"app store" "financial services" policy requirements Apple Google
```

### No-Action Letter Search
```
site:sec.gov "no-action" "[PRODUCT_TYPE]" OR "[COMPANY_TYPE]"
site:cftc.gov "no-action" "[PRODUCT_TYPE]"
site:cfpb.gov "no-action" "[PRODUCT_TYPE]"
```

### Output Table

| Primitive | Jurisdiction | Applicable Law | Citation | Status | Temporal Tag |
|---|---|---|---|---|---|
| FLOW_OF_FUNDS | US Federal | Bank Secrecy Act, FinCEN MSB | 31 USC §5311 | Active | [CURRENT_LAW] |
| FLOW_OF_FUNDS | US-NY | BitLicense | 23 NYCRR 200 | Active | [CURRENT_LAW] |
| USER_IDENTITY | EU | GDPR | Reg. 2016/679 | Active | [CURRENT_LAW] |
| ... | ... | ... | ... | ... | ... |

---

## Phase 3: MAP GATEWAYS

### Goal
Identify every license, registration, and framework required to operate.

### Separate into two categories:

**A. Statutory Gateways (Government-Enforced)**

| Gateway | Jurisdiction | Primitive | Est. TTC | Est. Capital | Penalty for Non-Compliance |
|---|---|---|---|---|---|
| MSB Registration | US Federal | FLOW_OF_FUNDS | 2-4 weeks | $0 (free) | Criminal (18 USC §1960) |
| State MTL (per state) | US States | FLOW_OF_FUNDS | 6-24 months | $25K-$1M+ surety bonds | Criminal (state-dependent) |
| EMI License | EU | FLOW_OF_FUNDS | 6-12 months | €350K min capital | Civil penalties |
| VASP Registration | EU (MiCA) | TOKEN_ISSUANCE | 3-6 months | Varies | Operating ban |
| ... | ... | ... | ... | ... | ... |

**B. Commercial Gateways (B2B/Contractually-Enforced)**

| Framework | Required By | Primitive | Est. TTC | Est. Capital | Consequence |
|---|---|---|---|---|---|
| SOC 2 Type I | Enterprise customers | DATA_STORAGE | 4-8 weeks | $15-50K | Lost deals |
| SOC 2 Type II | Enterprise customers | DATA_STORAGE | 6-12 months | $30-100K | Lost deals |
| PCI DSS Level 1 | Card networks | FLOW_OF_FUNDS | 3-6 months | $50-200K | Processing ban |
| ISO 27001 | EU enterprise | DATA_STORAGE | 6-12 months | $30-100K | Lost deals |
| ... | ... | ... | ... | ... | ... |

---

## Phase 4: GRAY ZONES & PENALTY LANDSCAPE

### Goal
Map areas of legal ambiguity with historical enforcement data and safe harbors.

### WebSearch Queries
```
"[PRODUCT_TYPE]" enforcement action penalty fine [JURISDICTION]
"[PRODUCT_TYPE]" "cease and desist" [REGULATORY_BODY]
"[PRODUCT_TYPE]" settlement consent order [REGULATORY_BODY]
"[PRODUCT_TYPE]" "safe harbor" OR exemption OR exception
"[PRODUCT_TYPE]" "regulatory sandbox" [JURISDICTION]
```

### "Extremes & Havens" State Map (For US State-Level Issues)

Instead of 50-state survey, identify three data points:

| Position | State | Why | Implication |
|---|---|---|---|
| **Strictest Outlier** | e.g., NY (BitLicense) | Most onerous requirements | Worst-case compliance cost |
| **Regulatory Haven** | e.g., WY (DAO laws) | Most favorable framework | Easiest launch jurisdiction |
| **Hyper-Local Trap** | e.g., IL (BIPA) | Obscure law with massive class-action risk | Must specifically avoid or comply |

### Penalty Landscape Table

| Violation Type | Regulator | Typical Penalty | Criminal/Civil | Historical Enforcement Frequency |
|---|---|---|---|---|
| Unregistered money transmission | FinCEN | $100K-$1M+ | Criminal (federal) | HIGH — actively enforced |
| GDPR breach notification failure | DPA | Up to 4% global revenue | Civil | MEDIUM — major cases only |
| Unlicensed securities offering | SEC | Disgorgement + penalties | Civil (can refer criminal) | HIGH for crypto |
| BIPA violation (IL) | Private right of action | $1K-5K per violation | Civil (class action) | HIGH — active plaintiff bar |
| ... | ... | ... | ... | ... |

---

## Phase 5: SYNTHESIS — The Cartographer's Matrix

### 5A. Product Profile

```
Product:        [DESCRIPTION]
Primitives:     [LIST]
Jurisdictions:  [LIST]
Complexity:     [RATING]
```

### 5B. Criminal Blockers (HARD STOP)

| Blocker | Law | Jurisdiction | Why It's Criminal | Action Required |
|---|---|---|---|---|
| e.g., OFAC violation | IEEPA | US | Sanctions evasion | Implement OFAC screening |
| e.g., AML failure | BSA | US | Money laundering facilitation | Implement AML program |

*If none: "No criminal blockers identified for this product configuration."*

### 5C. Statutory Gateways (with TTC & Capital)

| Priority | Gateway | Jurisdiction | TTC | Capital | Pre-Launch? | Temporal Tag |
|---|---|---|---|---|---|---|
| P0 | [License] | [Jurisdiction] | X months | $X | Yes/No | [tag] |
| P1 | ... | ... | ... | ... | ... | ... |

### 5D. Commercial Gateways

| Priority | Framework | Required By | TTC | Capital | Pre-Launch? |
|---|---|---|---|---|---|
| P0 | [Framework] | [Who requires it] | X months | $X | Yes/No |

### 5E. Gray Zones & Arbitrage Map

| Issue | Current Position | Gray Because... | Historical Penalty | Safe Harbor Option |
|---|---|---|---|---|
| [issue] | [current regulatory stance] | [why ambiguous] | [typical fine] | [alternative jurisdiction or structure] |

### 5F. Regulatory Sandbox Opportunities

| Sandbox | Jurisdiction | Eligibility | Duration | Benefits |
|---|---|---|---|---|
| e.g., FCA Sandbox | UK | Fintech with novel products | 12 months | Lighter compliance during test |
| e.g., MAS Sandbox | Singapore | Payment/crypto services | 6-12 months | Exemption from certain requirements |

### 5G. Pending Legislation (Monitor List)

| Bill/Proposal | Jurisdiction | Status | Expected Timeline | Impact If Passed |
|---|---|---|---|---|
| [bill] | [jurisdiction] | [introduced/committee/floor] | [est. date] | [how it changes the landscape] |

### 5H. Extremes & Havens Map (US State-Level)

| Issue | Strictest | Haven | Hyper-Local Trap |
|---|---|---|---|
| Money Transmission | NY (BitLicense) | WY (exemptions) | — |
| Biometric Data | IL (BIPA) | Most states (no law) | TX (CUBI) |
| AI/Automated Decisions | CO (SB21-169) | Most states (no law) | — |
| Data Privacy | CA (CPRA) | Most states (no comprehensive law) | — |

### 5I. Compliance Roadmap (Prioritized by TTC)

```
IMMEDIATE (Before Launch):
  □ [Action] — [TTC] — [Cost] — [Why now]
  □ [Action] — [TTC] — [Cost] — [Why now]

SHORT-TERM (First 6 Months):
  □ [Action] — [TTC] — [Cost] — [Why now]

MEDIUM-TERM (6-18 Months):
  □ [Action] — [TTC] — [Cost] — [Why now]

ONGOING:
  □ [Recurring obligation] — [Frequency] — [Annual cost]
```

### 5J. Data Gaps & Recommended Legal Counsel

```
GAPS:
- [GAP]: Specific state-level requirements for [X] not fully surveyed
- [GAP]: Shadow regulation via [partner type] not researched
- [GAP]: Non-English jurisdiction [X] requires native-language review

RECOMMENDED COUNSEL SPECIALTIES:
- [Specialty] attorney for [jurisdiction] — covers [primitives]
- [Specialty] attorney for [jurisdiction] — covers [primitives]
```

### 5K. Sources

```
Primary Government Sources:
  - [urls]

Agency Guidance & No-Action Letters:
  - [urls]

Industry Frameworks:
  - [urls]

Enforcement Actions:
  - [urls]
```

---

## Anti-Patterns (DO NOT)

| Anti-Pattern | Why It Fails |
|---|---|
| Providing specific legal advice | AI is not a lawyer — always disclaim |
| Using law firm blogs as objective truth | Biased marketing — either fear-mongering or permissive |
| Blending jurisdictions into a hybrid | Creates fictional composite regulations |
| Treating enforcement precedent as current law | Enforcement lags 3-5 years behind current priorities |
| Treating SOC2/PCI as laws | Commercial frameworks, not statutes — different enforcement |
| 50-state survey in one pass | Context window exhaustion — use Extremes & Havens |
| Downgrading agency guidance | Startups can't litigate to SCOTUS — guidance IS the law |
| Ignoring shadow regulation | BaaS/sponsor bank TPRM often stricter than direct regulation |
| Siloed industry triggers | Products cross domains — decompose into primitives |
| Making go/no-go recommendations | Map the terrain, let the human decide the path |

---

## Example Invocations

```
User: "regulatory landscape for a crypto payment app in the US and EU"
→ Primitives: [FLOW_OF_FUNDS] [TOKEN_ISSUANCE] [USER_IDENTITY]
→ Jurisdictions: US Federal, key US states, EU (MiCA, PSD2)
→ Heavy Phase 3 (MTLs, MiCA CASP, EMI)

User: "what licenses do I need for a fintech BaaS product"
→ Primitives: [FLOW_OF_FUNDS] [USER_IDENTITY] [DATA_STORAGE]
→ Shadow regulation search: sponsor bank TPRM
→ Focus on indirect compliance via banking partner

User: "compliance requirements for an AI healthcare platform"
→ Primitives: [AUTONOMOUS_LOGIC] [HEALTHCARE] [DATA_STORAGE] [USER_IDENTITY]
→ Intersectional: EU AI Act + HIPAA + GDPR
→ FDA SaMD classification analysis

User: "is it legal to issue a token in the US"
→ Primitives: [TOKEN_ISSUANCE]
→ Heavy Howey Test analysis, SEC no-action letters
→ Exemption mapping (Reg D, Reg S, Reg A+)
```

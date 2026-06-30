---
name: prior-art
description: |
  Patent and IP landscape research skill for any technology domain.
  Dual-mode: (1) Discovery Architect generates CPC/IPC codes + Boolean
  search strings for user to execute in Google Patents/Lens.org, plus
  forward-citation tracing and NPL invalidation search.
  (2) Claim & Status Parser performs element-by-element claim charting
  against product spec, legal status check, NPE detection, continuation
  trap analysis, and Section 101 Alice/Mayo screening.
  Trigger: "prior art", "patent landscape", "patent search",
  "IP landscape", "freedom to operate", "FTO", "patent research".
  DO NOT activate for: General business strategy, trademark questions,
  copyright disputes, or simple "who owns this patent" lookups.
---

# Prior Art & IP Landscape Research Skill

> Claude is a Query Engineer, NOT a database scraper. It generates search
> strings and classification maps for the user to execute in patent databases.
> It parses claims and legal status with surgical precision. It never scrapes
> dynamic patent GUIs, never declares legal conclusions, and never combines
> prior art references without documented "motivation to combine."

## Activation

```
ACTIVATE when user says:
  "prior art", "patent landscape", "patent search", "IP landscape",
  "freedom to operate", "FTO", "patent research", "claim chart",
  "patent invalidation", "prior art search for [X]",
  "is [X] patented", "patent risk", "IP risk assessment"

DO NOT activate for:
  - Trademark / copyright questions → refuse or redirect
  - "Who owns patent X" without deeper analysis → use WebSearch directly
  - General business strategy → use /competitive-analysis
  - Simple patent number lookup → use WebSearch directly
  - Legal advice → refuse with disclaimer
```

## Input

User provides a **technical description or patent number** (required) and optionally:
- Mode selection ("find prior art" vs "analyze this patent")
- Specific patent number(s) for Mode 2 analysis
- Product specification for FTO charting
- Jurisdiction preference (US default, EPO, WIPO, JPO)
- Time constraint ("prior art before 2019-03-15")

If intent is ambiguous, ask: "Are you looking to (A) discover prior art / map a landscape, or (B) analyze a specific patent's claims against your product?"

---

## Core Design Principle

**Query Engineer + Claim Parser, NOT Web Scraper.**

Claude Code is a CLI-based agent. It cannot:
- Scrape dynamic JavaScript-rendered patent databases (Lens.org, PatSnap)
- Bypass CAPTCHA/Cloudflare on USPTO or Google Patents bulk queries
- Aggregate thousands of patents into statistical landscape maps
- Provide legally binding Freedom-to-Operate opinions

It CAN:
- Translate plain-English inventions into CPC/IPC classification codes
- Generate syntactically perfect Boolean search strings for patent databases
- Trace forward citations from user-provided foundational patent numbers
- Search NPL sources (arXiv, Semantic Scholar, GitHub) for invalidation art
- Parse individual patent claims element-by-element against product specs
- Detect NPE signatures, continuation traps, and legal status issues
- Apply Section 101 Alice/Mayo screening to software/method claims
- Flag hindsight bias in prior art combinations

---

## Confidence Tagging System (4-Tier)

| Tag | Criteria | When to Use |
|-----|----------|-------------|
| `[VERIFIED]` | Directly confirmed from patent office record or official source | Legal status, priority dates, assignee from USPTO/EPO |
| `[SEARCH_DERIVED]` | Found via WebSearch from reputable IP source | Patent family data from Google Patents, NPL from arXiv |
| `[ANALYST_INFERENCE]` | Reasoned from available data — flagged for user verification | CPC code selection, NPE probability, claim element mapping |
| `[UNKNOWN]` | Data not reliably found after 3+ targeted searches | Maintenance fee status, specific licensing terms |

**Critical rule**: Never assign `[VERIFIED]` to any data not sourced from an official patent office record or the patent document itself. WebSearch results from blogs or news are `[SEARCH_DERIVED]` at best.

---

## The Hindsight Bias Guardrail (MANDATORY)

```
⚠ HINDSIGHT BIAS PROTOCOL — ENFORCED IN ALL PRIOR ART ANALYSIS

When identifying prior art references:
1. NEVER combine two or more references to argue obviousness UNLESS
   Reference A explicitly cites or references Reference B, OR
   both references appear in the same survey/textbook establishing
   the combination as known in the art.

2. For each reference, state independently:
   "Reference X, standing alone, discloses elements [A, B] but NOT [C]."

3. If combining references, you MUST document:
   "Motivation to combine: [specific textual evidence from the prior art
   itself that suggests this combination, NOT from the target invention]."

4. If no motivation to combine exists in the prior art, state:
   "These references are presented individually. No documented motivation
   to combine was found in the prior art itself. Combining them requires
   legal analysis beyond this tool's scope."
```

---

## Mode Selection Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     /PRIOR-ART SKILL                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────┐  ┌─────────────────────────┐       │
│  │  MODE 1                 │  │  MODE 2                 │       │
│  │  DISCOVERY ARCHITECT    │  │  CLAIM & STATUS PARSER  │       │
│  │  (High Recall)          │  │  (High Precision)       │       │
│  │                         │  │                         │       │
│  │  Input: Technical desc  │  │  Input: Patent number + │       │
│  │                         │  │  product specification  │       │
│  │  Output:                │  │                         │       │
│  │  • CPC/IPC codes        │  │  Output:                │       │
│  │  • Boolean strings      │  │  • Legal status         │       │
│  │  • Forward citation map │  │  • Priority date chain  │       │
│  │  • NPL search results   │  │  • NPE assessment      │       │
│  │  • Lexicon thesaurus    │  │  • Continuation trap    │       │
│  │                         │  │  • Claim element chart  │       │
│  │  User executes search   │  │  • Section 101 screen   │       │
│  │  in external database   │  │  • IP strategy signal   │       │
│  └─────────────────────────┘  └─────────────────────────┘       │
│                                                                  │
│  BOTH MODES: Hindsight Bias Guardrail + Legal Disclaimer         │
└──────────────────────────────────────────────────────────────────┘
```

---

## Mode 1: Discovery Architect (High Recall)

### Goal
Translate the user's invention into every search dimension a patent professional uses: classification codes, obfuscated lexicon, Boolean syntax, forward citations, and non-patent literature. Claude generates the queries; the user executes them.

### Phase 1A: CPC/IPC Classification Map

Identify the relevant Cooperative Patent Classification codes for the invention. CPC codes are the *actual* structural bypass for patent lexicon obfuscation — they group patents by technology regardless of the drafter's word choices.

#### WebSearch Queries
```
"[TECHNOLOGY]" CPC classification patent
CPC code "[TECHNOLOGY CONCEPT]" site:uspto.gov OR site:cooperativepatentclassification.org
"[TECHNOLOGY]" IPC classification WIPO
```

#### Output Table — Classification Map

| CPC/IPC Code | Description | Relevance | Confidence |
|---|---|---|---|
| G06F 16/00 | Information retrieval; Database structures | PRIMARY | [ANALYST_INFERENCE] |
| H04L 9/32 | Cryptographic mechanisms | SECONDARY | [ANALYST_INFERENCE] |
| G06N 3/08 | Learning methods for neural networks | TERTIARY | [ANALYST_INFERENCE] |

**Provide 3-8 codes**, ranked by relevance. Always include at least one PRIMARY (core technology), one SECONDARY (adjacent), and one TERTIARY (unexpected angle that patent drafters might file under).

### Phase 1B: Patent Lexicon Thesaurus

Patent drafters intentionally use obfuscated language. Map the user's plain-English terms to the idiosyncratic vocabulary patent attorneys actually use.

#### Output Table — Lexicon Map

| Plain English | Patent-ese Variants | Notes |
|---|---|---|
| smartphone | mobile communication terminal, portable electronic device, handheld computing apparatus | Broadening terms |
| database | data store, persistent storage means, information repository | Abstract terms preferred |
| machine learning | trained computational model, adaptive classification system | Avoids "AI" which is too broad |

### Phase 1C: Boolean Search Strings

Generate copy-paste-ready Boolean search strings for the user to execute in Google Patents, Lens.org, or Espacenet.

#### Google Patents Format
```
((CPC=G06F16/00) OR (CPC=H04L9/32))
AND ("data store" OR "persistent storage" OR "information repository")
AND ("trained model" OR "adaptive classification" OR "machine learning")
AND (COUNTRY=US)
AND (AFTER=priority-date-minus-1-year)
```

#### Lens.org Format
```
classification_cpc:(G06F16* OR H04L9/32*)
AND title_abstract:("data store" OR "persistent storage")
AND title_abstract:("trained model" OR "adaptive classification")
AND jurisdiction:(US)
```

**Generate 3-5 variants** with different specificity levels:
1. **Narrow** (high precision): All primary CPC codes AND core terms
2. **Medium**: Primary + secondary CPC codes, broader terms
3. **Wide** (high recall): All CPC codes, full lexicon thesaurus, no date filter

### Phase 1D: Forward Citation Tracing

If the user provides a foundational patent number, trace its forward citations to map active competitors and technology evolution.

#### WebSearch Queries
```
"[PATENT_NUMBER]" cited by OR "forward citations"
"[PATENT_NUMBER]" site:patents.google.com
"[PATENT_NUMBER]" patent family citations
```

#### Output Table — Forward Citation Map

| Citing Patent | Assignee | Year | Key Advance Over Foundational | Confidence |
|---|---|---|---|---|
| US20XX... | Company A | 20XX | Added [feature] | [SEARCH_DERIVED] |
| US20XX... | Company B | 20XX | Applied to [domain] | [SEARCH_DERIVED] |

### Phase 1E: Non-Patent Literature (NPL) Search

NPL is the primary invalidation weapon. Patent examiners routinely miss academic papers, open-source repos, and standards documents.

#### WebSearch Queries
```
"[TECHNOLOGY]" "[KEY_CONCEPT]" site:arxiv.org
"[TECHNOLOGY]" "[KEY_CONCEPT]" site:semanticscholar.org
"[TECHNOLOGY]" "[KEY_CONCEPT]" site:github.com
"[TECHNOLOGY]" "[STANDARD_BODY]" specification standard
"[TECHNOLOGY]" "[KEY_CONCEPT]" conference paper proceedings
```

**Critical**: For every NPL result, extract and prominently display the **publication date**. An NPL reference published one day after the priority date is legally useless.

#### Output Table — NPL Prior Art Candidates

| Source | Title | Publication Date | Pre-dates Priority? | Key Disclosure | Confidence |
|---|---|---|---|---|---|
| arXiv | Paper title | YYYY-MM-DD | YES/NO/UNKNOWN | Discloses elements [X, Y] | [SEARCH_DERIVED] |
| GitHub | Repo/commit | YYYY-MM-DD | YES/NO/UNKNOWN | Implements [feature] | [SEARCH_DERIVED] |

---

## Mode 2: Claim & Status Parser (High Precision)

### Goal
Given a specific patent number and optionally a product specification, perform surgical analysis: legal status, entity profiling, claim decomposition, element-by-element charting, and patentability screening.

### Phase 2A: Patent Status & Chronology

#### WebSearch Queries
```
"[PATENT_NUMBER]" legal status active expired abandoned
"[PATENT_NUMBER]" maintenance fee paid site:uspto.gov
"[PATENT_NUMBER]" priority date filing date
"[PATENT_NUMBER]" patent family continuations pending
"[PATENT_NUMBER]" site:patents.google.com
```

#### Output Table — Patent Vitals

| Field | Value | Confidence |
|---|---|---|
| Patent Number | USXXXXXXXX | [VERIFIED] |
| Title | ... | [VERIFIED] |
| Assignee (Current) | Company Name | [SEARCH_DERIVED] |
| Filing Date | YYYY-MM-DD | [VERIFIED] |
| Priority Date (Earliest) | YYYY-MM-DD | [VERIFIED] |
| Grant Date | YYYY-MM-DD | [VERIFIED] |
| Expiration Date (Calculated) | YYYY-MM-DD | [ANALYST_INFERENCE] |
| Legal Status | Active / Expired / Fee-Lapsed / Abandoned | [SEARCH_DERIVED] |
| Maintenance Fees Current? | Yes / No / Unknown | [SEARCH_DERIVED] |

```
⚠ CHRONOLOGY PROTOCOL — ENFORCED
Priority Date (earliest) = the legal threshold for prior art.
NOT the publication date. NOT the grant date.
Trace back through: provisional → PCT → national phase → continuations.
Any prior art MUST pre-date the earliest priority date.
```

### Phase 2B: Patent Family & Continuation Trap Analysis

#### WebSearch Queries
```
"[PATENT_NUMBER]" continuation patent family
"[PATENT_NUMBER]" "continuation-in-part" OR "divisional" OR "PCT"
"[ASSIGNEE]" patent applications pending site:appft.uspto.gov
```

#### Output Table — Family Analysis

| Family Member | Type | Status | Key Difference from Parent | Risk Level |
|---|---|---|---|---|
| US20XX/XXXXXXX | Continuation | PENDING | Claims broadened to cover [X] | CRITICAL |
| EPXXXXXXXX | National Phase | Granted | Narrower claims (EPO) | MEDIUM |
| PCTXXXXXXXX | PCT | Expired | — | NONE |

```
⚠ CONTINUATION TRAP FLAG
If ANY family member has status = PENDING:
"WARNING: Open patent family detected. The assignee can still file new
claims specifically targeting your product. This patent family is MORE
dangerous than the granted patent alone."
```

### Phase 2C: NPE / Patent Troll Detection

#### WebSearch Queries
```
"[ASSIGNEE]" products OR services OR revenue
"[ASSIGNEE]" patent litigation OR lawsuit OR "patent infringement"
"[ASSIGNEE]" "non-practicing entity" OR "patent assertion entity" OR NPE
"[ASSIGNEE]" number of patents portfolio size
```

#### NPE Signature Checklist

| Signal | Finding | NPE Indicator? |
|---|---|---|
| Consumer products or services? | Yes/No | No products = NPE signal |
| Number of patents in portfolio | N | >200 with no products = strong NPE signal |
| Entity type | LLC / Corp / University / Individual | Generic LLC name = NPE signal |
| Litigation volume | N lawsuits | >10 patent suits = strong NPE signal |
| Physical presence | Office / Shell / PO Box | Delaware/East Texas shell = NPE signal |
| Revenue source | Products / Licensing / Litigation | Litigation-only = NPE confirmed |

#### Output
```
NPE Risk Assessment: HIGH / MEDIUM / LOW / NOT AN NPE
Reasoning: [2-3 sentences with evidence]
Implication: [What this means for the user's FTO strategy]
```

### Phase 2D: Section 101 Alice/Mayo Screening (Software/Method Patents)

For software, business method, or diagnostic method patents, evaluate subject matter eligibility before any FTO analysis.

#### Alice/Mayo Two-Step Test

```
Step 1: Is the claim directed to an abstract idea, law of nature,
        or natural phenomenon?
        □ Mathematical concept / algorithm
        □ Method of organizing human activity
        □ Mental process performable in the human mind
        → If YES, proceed to Step 2
        → If NO, claim is likely Section 101 eligible

Step 2: Does the claim recite an "inventive concept" that transforms
        the abstract idea into a patent-eligible application?
        □ Specific technical improvement to computer functionality
        □ Particular machine or manufacture tied to the method
        □ Transformation of a particular article to a different state
        → If YES, claim likely survives Alice
        → If NO, claim is vulnerable to Section 101 challenge

Assessment: LIKELY ELIGIBLE / VULNERABLE / LIKELY INELIGIBLE
Reasoning: [Cite specific claim language and analogous case outcomes]
```

**Jurisdictional note**: This test applies to US patents only. For EPO patents, apply the "Technical Effect" doctrine instead. For other jurisdictions, state the applicable standard or mark `[UNKNOWN]`.

### Phase 2E: Claim Element Chart (FTO Analysis)

**Prerequisite**: User must provide both the patent claim text AND their product specification. If either is missing, request it before proceeding.

#### Output Table — Element-by-Element Claim Chart

| Claim Element | Claim Language (Verbatim) | Product Feature | Reads On? | Analysis | Confidence |
|---|---|---|---|---|---|
| Preamble | "A method for..." | Product does X | YES/NO/PARTIAL | [reasoning] | [ANALYST_INFERENCE] |
| Element A | "receiving, by a processor..." | Product receives via API | YES | Literal match | [ANALYST_INFERENCE] |
| Element B | "transforming using a trained model..." | Product uses rule engine | NO | No ML component | [ANALYST_INFERENCE] |
| Element C | "outputting to a display..." | Product outputs to terminal | PARTIAL | Arguable — CLI vs display | [ANALYST_INFERENCE] |

**FTO Signal** (NOT a legal opinion):
```
Elements reading on product: X of Y
Missing elements: [list]
Overall signal: HIGH RISK / MODERATE RISK / LOW RISK / LIKELY CLEAR

⚠ DISCLAIMER: This is a technical mapping exercise, NOT a legal
Freedom-to-Operate opinion. Claim construction requires Markman hearing
precedent and prosecution history estoppel analysis that is beyond this
tool's capability. Consult a patent attorney for actionable FTO.
```

---

## IP Strategy Assessment (Both Modes)

After completing the relevant mode, provide a strategic summary.

### Output Table — IP Strategy Signals

| Dimension | Assessment | Action Item |
|---|---|---|
| Landscape Density | Crowded / Sparse / Emerging | [Implication for filing] |
| Dominant Assignees | [Names] | [Licensing vs design-around] |
| NPE Exposure | High / Medium / Low | [Litigation risk] |
| Continuation Risk | Open families: Y/N | [Monitor these families] |
| NPL Invalidation Potential | Strong / Weak / Unknown | [Strongest NPL reference] |
| Section 101 Vulnerability | Eligible / Vulnerable / N/A | [Challenge opportunity] |
| Trade Secret Alternative | Viable / Not viable | [Detectability assessment] |
| Jurisdiction Gaps | [Where protection is weak] | [Filing strategy] |

---

## Search Strategy Rules

1. **CPC codes first**: Always identify classification codes before generating keyword searches — codes bypass lexicon obfuscation structurally
2. **Generate, don't scrape**: Output Boolean strings for the user to execute in Google Patents / Lens.org — never attempt to scrape dynamic patent databases
3. **Forward citations > backward keywords**: One good foundational patent + forward tracing beats 50 keyword searches
4. **NPL is the weapon**: arXiv, Semantic Scholar, GitHub, IEEE, ACM, standards bodies — patent examiners miss these
5. **Chronology is sacred**: Every reference must have its publication date verified against the earliest priority date
6. **Legal status first**: Check if the patent is alive before spending time on claim analysis
7. **Domain targeting** for WebSearch:
   - `site:patents.google.com` — full patent text, legal status, citations
   - `site:uspto.gov` — official records, PAIR, maintenance fees
   - `site:arxiv.org` — pre-print NPL (check submission date, not revision date)
   - `site:semanticscholar.org` — academic NPL with citation context
   - `site:github.com` — code-level NPL (commit dates = publication dates)
   - `site:lens.org` — only for specific patent lookups, NOT bulk scraping
8. **Recency**: Patent landscapes shift — check for continuation filings in the last 18 months
9. **Never fabricate patent numbers**: If a patent number is not found, mark `[UNKNOWN]` — do not guess
10. **Jurisdiction awareness**: Default to US (USPTO) unless user specifies otherwise. Always note if analysis is jurisdiction-specific

---

## Anti-Patterns (DO NOT)

| Anti-Pattern | Why It Fails |
|---|---|
| Scraping Lens.org or PatSnap for aggregate data | JS-rendered, Cloudflare-protected — Claude will hit CAPTCHA and return garbage |
| Pure semantic search without CPC codes | LLM embeddings are not trained on patent-ese — "mobile communication terminal" maps to "airport" not "smartphone" |
| Declaring definitive FTO ("you are safe to build") | FTO is a legal conclusion requiring Markman hearing analysis — Claude provides signals, not opinions |
| Combining 3 NPL references to argue "obvious" | Hindsight bias — must have documented "motivation to combine" from the prior art itself |
| Summarizing claim "boundaries" instead of element-by-element charting | Broadens claims, creates false-positive risk clusters, paralyzes engineering teams |
| Using publication date as prior art threshold | Priority date (earliest provisional/PCT) is the legal threshold — can be years before publication |
| Ignoring legal status of a patent | Over 50% of granted patents expire from unpaid maintenance fees — dead IP is not a threat |
| Advising "patent this" based solely on detectability | Section 101 Alice/Mayo renders many software methods unpatentable regardless of detectability |
| Treating granted claims as final | Open continuations mean the assignee can rewrite claims tomorrow to target your product |
| Performing multi-step date arithmetic without flagging | Priority date chains cross provisionals, PCTs, continuations — always tag `[ANALYST_INFERENCE]` |
| Reporting landscape statistics from WebSearch | You cannot aggregate 5,000 patents into filing trends from web snippets — generate the query, let the user run it |
| Mixing US and EPO legal standards | Section 101 (Alice/Mayo) and EPO "Technical Effect" are fundamentally different — never blend them |

---

## WebSearch Templates

### Mode 1 — Discovery
```
# CPC Code Identification
"[TECHNOLOGY]" CPC classification cooperative patent
"[CONCEPT]" patent classification code G06 OR H04 OR G16

# Foundational Patent Forward Citations
"[PATENT_NUMBER]" "cited by" OR "forward citations" site:patents.google.com

# NPL — Academic
"[CONCEPT_A]" "[CONCEPT_B]" site:arxiv.org [YEAR_RANGE]
"[CONCEPT_A]" "[CONCEPT_B]" site:semanticscholar.org
"[CONCEPT_A]" "[CONCEPT_B]" conference proceedings IEEE OR ACM

# NPL — Code
"[CONCEPT]" "[IMPLEMENTATION]" site:github.com created:<PRIORITY_DATE

# NPL — Standards
"[TECHNOLOGY]" specification standard "[STANDARDS_BODY]"
```

### Mode 2 — Analysis
```
# Patent Status
"[PATENT_NUMBER]" legal status maintenance fee site:patents.google.com
"[PATENT_NUMBER]" site:portal.uspto.gov

# Patent Family
"[PATENT_NUMBER]" continuation divisional patent family
"[PATENT_NUMBER]" "continuation-in-part" OR CIP

# Assignee NPE Check
"[ASSIGNEE]" products services revenue customers
"[ASSIGNEE]" patent litigation infringement lawsuit
"[ASSIGNEE]" "non-practicing entity" OR "patent troll" OR NPE

# Section 101 Case Law (for software patents)
"[PATENT_TECHNOLOGY]" Alice Mayo "abstract idea" "patent eligible"
```

---

## Output Structure

### Mode 1 Output Sections
1. Mode Selection Confirmation
2. CPC Classification Map (Phase 1A)
3. Patent Lexicon Thesaurus (Phase 1B)
4. Boolean Search Strings — 3-5 variants (Phase 1C)
5. Forward Citation Map (Phase 1D, if foundational patent provided)
6. NPL Prior Art Candidates (Phase 1E)
7. IP Strategy Assessment
8. Data Gaps & Caveats
9. Sources

### Mode 2 Output Sections
1. Mode Selection Confirmation
2. Patent Vitals & Legal Status (Phase 2A)
3. Patent Family & Continuation Trap (Phase 2B)
4. NPE Risk Assessment (Phase 2C)
5. Section 101 Screening (Phase 2D, if software/method patent)
6. Claim Element Chart (Phase 2E, if product spec provided)
7. IP Strategy Assessment
8. Data Gaps & Caveats
9. Sources

### Mandatory Footer (Both Modes)
```
⚠ LEGAL DISCLAIMER
This analysis is a technical research aid, NOT legal advice. It does not
constitute a Freedom-to-Operate opinion, patentability assessment, or
invalidity opinion. Patent claim construction, prosecution history
estoppel, doctrine of equivalents, and jurisdictional nuances require
analysis by a licensed patent attorney. Use this output to inform — not
replace — professional legal counsel.

Sources:
  Official Records: [urls]
  Patent Databases: [urls]
  NPL Sources: [urls]
  WebSearch Results: [urls]
```

---

## Example Invocations

```
User: "prior art search for a system that uses LLMs to generate
       database queries from natural language"
→ Mode 1: Full Discovery Architect output with CPC codes (G06F 16/,
  G06N 3/), lexicon map, 5 Boolean strings, NPL from arXiv/GitHub

User: "analyze patent US11,423,087 against our product"
→ Mode 2: Full Claim & Status Parser — legal status, family tree,
  NPE check, Section 101 screen, then request product spec for
  element-by-element charting

User: "FTO assessment for our AI-powered contract analysis tool"
→ Ask: "Do you have specific patent numbers to analyze, or should I
  start with a discovery search to identify relevant patents first?"
  Then route to Mode 1 or Mode 2 accordingly

User: "patent landscape for federated learning"
→ Mode 1: Heavy on CPC classification (H04L, G06N), wide Boolean
  strings, forward citations from foundational FL papers/patents,
  deep NPL sweep (McMahan et al. 2017, etc.)

User: "is our blockchain bridge design safe to build"
→ Mode 1 first (discover relevant patents), then Mode 2 on the
  highest-risk patents found. Flag continuation traps heavily in
  the blockchain/crypto patent space (many open families).
```

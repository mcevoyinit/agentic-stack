---
name: person-research
description: |
  Discrepancy Engine for researching individuals — founders, executives,
  investors, or public figures. Maps narrative friction between self-reported
  claims and third-party sources, surfaces chronological gaps, tracks social
  graph density, and generates targeted interrogation questions. NOT a
  background-check replacement — an interrogation-prep tool that arms the
  user with the exact questions to ask during human-led diligence.
  Trigger: "person research", "who is", "background on [person]",
  "founder research", "research [person]", "person DD", "people diligence".
  DO NOT activate for: General "tell me about X" without diligence context,
  celebrity gossip, social media stalking, or requests for private PII.
---

# Person Research — The Discrepancy Engine

> All public data is curated, biased, or incomplete. The highest value an AI
> can deliver is not declaring truth — it is mapping the friction between
> sources and generating the exact questions a human needs to ask. This skill
> is an interrogation-prep tool, not an oracle.

## Activation

```
ACTIVATE when user says:
  "person research", "who is [person]", "background on [person]",
  "founder research", "research [person]", "person DD",
  "people diligence on", "deep dive on [person]"

DO NOT activate for:
  - General "tell me about X" without investment/hiring context → use WebSearch
  - Celebrity gossip or personal life questions → refuse
  - Requests for private addresses, phone numbers, or SSNs → refuse
  - Simple LinkedIn lookup → use WebSearch directly
```

## Input

User provides a **person's name** (required) and optionally:
- Company affiliation ("the CEO of Acme Corp")
- Temporal anchor ("the John Chen who was at Stripe in 2019")
- Research context ("for a Series B co-invest", "we're hiring them as CTO")
- Specific concern ("I heard they left their last company under bad terms")
- Related persons to cross-reference ("and their co-founder Jane Doe")

If the name alone is ambiguous, HALT and ask for disambiguation anchors.

---

## Core Design Principles

### 1. The Discrepancy Engine Paradigm
This skill does NOT attempt to calculate objective truth, produce risk scores,
or deliver a pass/fail verdict. It assumes all public data is curated and
potentially misleading. Its primary output is **narrative friction** — the
deltas between what different sources claim about the same person. The user
decides what is true; the skill decides what questions to ask.

### 2. Source Hierarchy (Enforced, Not Advisory)
Every claim in the output MUST be tagged with its source tier:

| Tier | Label | Examples | Epistemology |
|------|-------|----------|-------------|
| T1 | `[REGULATORY]` | SEC Form D, patent filings, court records, incorporation docs | Official records; lawsuits are ALLEGATIONS, not facts |
| T2 | `[CORROBORATED]` | Crunchbase, Bloomberg, PitchBook, Google Scholar, news wire (AP/Reuters) | Third-party databases; may contain stale or gamed data |
| T3 | `[SELF-REPORTED]` | LinkedIn, personal website, Twitter/X, Forbes profiles, TEDx, podcasts | Curated self-narrative; treat as marketing until corroborated |

When T3 contradicts T1 or T2, the skill MUST flag it as a discrepancy.
Never average conflicting claims. Present both with sources.

### 3. Synthetic Credibility Awareness
The AI MUST recognize reputation management artifacts for what they are:
- Forbes 30 Under 30, TEDx talks, Inc 5000 = **marketing signals**, not competence proof
- SEO-optimized press releases and "thought leadership" articles = curated narrative
- Crunchbase profiles can be self-edited; funding amounts may be inflated or fabricated
- Court filings of dummy SEC Form Ds exist to manufacture legitimacy

Tag these as `[SYNTHETIC CREDIBILITY]` when encountered.

### 4. The Quiet Operator Exception
Do NOT penalize deep-tech founders, quant researchers, senior engineers, or
operators for low social media presence. A dense patent portfolio or highly
cited Google Scholar profile outweighs 50K Twitter followers. Contextualize
online presence by industry norms:
- Deep-tech / Research → Scholar citations, patents, conference talks
- Consumer / Social → Twitter, podcast, media presence
- Enterprise / B2B → LinkedIn activity, conference keynotes
- Finance / Investing → SEC filings, Bloomberg, portfolio outcomes

### 5. Legal Epistemology
- Lawsuits are **allegations**, not facts. Always label as `[ALLEGED]`
- Filter for material suits: fraud, breach of fiduciary duty, IP theft, harassment
- Ignore frivolous/patent-troll litigation that any long-tenured CEO accumulates
- Settlements are not admissions of guilt — note them neutrally
- Distinguish plaintiff vs. defendant (LLMs frequently confuse these)

### 6. No Pseudo-Metrics
Do NOT compute:
- "Career Velocity" (penalizes long-term builders, rewards job-hoppers)
- "Influence Scores" (conflates marketing with competence)
- "Risk Scores" or "Credibility Ratings" (false precision from noisy data)
- "Outcome Ratios" (LLMs hallucinate dollar amounts from SEC filings)

The skill surfaces raw data and discrepancies. The human assigns meaning.

---

## Research Architecture (4 Phases)

```
+------------------------------------------------------------------+
|                   PERSON RESEARCH ENGINE                          |
+------------------------------------------------------------------+
|                                                                    |
|  Phase 0: DISAMBIGUATION GATE    Resolve identity before spending  |
|  ----------------------------    any research API calls             |
|                                                                    |
|  Phase 1: MAP-REDUCE INGESTION   LinkedIn, Crunchbase, open web,  |
|  ---------------------------     SEC, Scholar — summarize chunks    |
|                                                                    |
|  Phase 2: DISCREPANCY &          Cross-reference timelines, flag   |
|           OMISSIONS CHECK        "Missing 18 Months", title        |
|  ---------------------------     inflation, exit misrepresentation  |
|                                                                    |
|  Phase 3: SOCIAL GRAPH           Recurring co-founders, investors, |
|  ---------------------------     talent portability, network nodes  |
|                                                                    |
|  Phase 4: SYNTHESIS              Verified Timeline, Outcomes       |
|  ---------------------------     Ledger, Discrepancies, Questions   |
|                                                                    |
+------------------------------------------------------------------+
```

---

## Phase 0: Disambiguation Gate

### Goal
Resolve name collisions BEFORE spending any research calls. A poisoned
identity contaminates the entire context window and cannot be recovered.

### Procedure

1. Run a single scoping search:
```
"[FULL NAME]" AND ("[COMPANY]" OR "[INDUSTRY]" OR "[LOCATION]")
```

2. Evaluate ambiguity:
   - **Unique match** (uncommon name + clear affiliation) → proceed to Phase 1
   - **Ambiguous** (common name, multiple plausible matches) → HALT

3. If HALTED, present candidates to the user:
```
DISAMBIGUATION REQUIRED — multiple matches for "[NAME]":

  A) [Name] — CEO of Acme Corp (SF, founded 2019). LinkedIn: [url]
  B) [Name] — Partner at XYZ Capital (NYC, joined 2015). Crunchbase: [url]
  C) [Name] — Professor of CS at MIT. Scholar: [url]

Which person should I research? Or provide additional context
(company, location, time period) to narrow the match.
```

4. Do NOT proceed until identity is confirmed with at least TWO anchors:
   **Name + Company**, **Name + Time Period**, or **Name + Location/Industry**.

---

## Phase 1: Map-Reduce Ingestion

### Goal
Gather raw data from multiple sources, summarize each in isolation to avoid
context window degradation, then pass concise summaries forward.

### WebSearch Query Templates (Run ALL categories)

**1A. LinkedIn / Professional** `[SELF-REPORTED]`
```
site:linkedin.com/in "[FULL NAME]" "[COMPANY]"
"[FULL NAME]" resume OR biography "[COMPANY]"
```
Extract: roles, titles, date ranges, education, claims needing corroboration.

**1B. Crunchbase / Funding** `[CORROBORATED]` (note: profiles are self-editable)
```
site:crunchbase.com/person "[FULL NAME]"
"[FULL NAME]" "[COMPANY]" funding OR "series" OR "raised"
"[FULL NAME]" pitchbook OR dealroom profile
```
Extract: companies founded, board seats, investment portfolio, funding rounds.

**1C. Regulatory / Filings** `[REGULATORY]` (note: 13D/13G = PUBLIC companies only)
```
site:sec.gov "[FULL NAME]" OR "[COMPANY]"
"[FULL NAME]" SEC filing OR "form D" OR 13D OR proxy
"[FULL NAME]" patent site:patents.google.com
```
Extract: SEC Form D, patents, beneficial ownership, incorporation records.

**1D. Academic / Technical** `[CORROBORATED]`
```
"[FULL NAME]" site:scholar.google.com
"[FULL NAME]" research paper OR arxiv OR conference speaker
"[FULL NAME]" podcast interview OR "talks at"
```
Extract: papers, citations, conference talks, podcast positions. **Summarize
long-form content into bullets BEFORE passing to synthesis.**

**1E. Press / News** (tag Forbes/TEDx as `[SYNTHETIC CREDIBILITY]`)
```
"[FULL NAME]" "[COMPANY]" site:bloomberg.com OR site:reuters.com
"[FULL NAME]" "[COMPANY]" TechCrunch OR "The Information" OR Axios
"[FULL NAME]" Forbes OR "30 under 30"
```
Extract: wire coverage vs. puff pieces, negative coverage, departure reporting.

**1F. Shadow Data** (unvarnished sentiment)
```
"[FULL NAME]" OR "[COMPANY]" site:reddit.com OR site:news.ycombinator.com
"[FULL NAME]" OR "[COMPANY]" site:glassdoor.com OR site:teamblind.com
"[FULL NAME]" lawsuit OR sued OR litigation OR fraud OR controversy
"[FULL NAME]" fired OR resigned OR "stepped down" OR terminated
```
Extract: employee/community sentiment, legal proceedings (distinguish
plaintiff vs. defendant). **Filter lawsuits:** only fraud, fiduciary breach,
IP theft, harassment, securities violations. Ignore patent trolls.

---

## Phase 2: Discrepancy & Omissions Check

### Goal
Cross-reference the Phase 1 summaries against each other. Hunt for narrative
friction, chronological gaps, and inflated claims.

### 2A. Timeline Reconciliation

Lay out a unified chronology from ALL sources. Flag:

- **The "Missing 18 Months"**: Gaps between roles that appear on LinkedIn
  but are absent from Crunchbase/news. These often indicate scrubbed failures
  or short, disastrous stints.
  ```
  [GAP]: LinkedIn shows "Consultant" from 2017-2018. No company named.
  Crunchbase shows [COMPANY X] founded 2016, shut down 2017.
  QUESTION: Was the "consulting" period actually the wind-down of [COMPANY X]?
  ```

- **Title Inflation**: LinkedIn says "Co-Founder" but earliest Crunchbase
  press release or SEC Form D lists them as "VP Engineering" or "Early Employee."
  ```
  [DISCREPANCY]: LinkedIn claims Co-Founder of [COMPANY] (2015-present).
  Crunchbase seed round announcement (2015) lists only [OTHER PERSON] as founder.
  [FULL NAME] appears in "Team" section as "Head of Engineering" on archived
  company website (Wayback Machine, 2016).
  ```

- **Exit Misrepresentation**: Claims of "acquisition" when reality was
  acqui-hire, asset sale, or outright shutdown.
  ```
  [DISCREPANCY]: LinkedIn says "[COMPANY] — Acquired by [ACQUIRER]."
  TechCrunch (2019): "[ACQUIRER] acqui-hired 3 engineers from [COMPANY]
  as the startup wound down operations."
  ```

### 2B. Omissions Scan

Explicitly flag what is MISSING that should be present:

| Expected Data Point | Missing = Investigate Because |
|---|---|
| Company outcome for a past venture | May be hiding a failure |
| Education details (degree, year) | Possible credential inflation |
| Co-founder(s) for a "solo founder" claim | Were there co-founders who left? |
| References to board members | Governance gaps |
| Technical publications (for "AI expert" claims) | Expertise may be marketing |
| Revenue/traction at prior companies | Outcomes may be underwhelming |
| Reason for departure from prior role | May have been forced out |
| Patent filings (for "invented X" claims) | Check if patents actually exist |

---

## Phase 3: Social Graph

### Goal
Map the recurring nodes around the subject. Who moves with them? Who invests
in them repeatedly? Talent portability is one of the highest-signal,
verifiable indicators of leadership quality.

### WebSearch Queries
```
"[FULL NAME]" AND "[KNOWN ASSOCIATE]" company OR startup OR founded
"[FULL NAME]" co-founder worked together OR "joined from"
"[COMPANY 1]" AND "[COMPANY 2]" team OR employees
"[FULL NAME]" investor OR "backed by" OR "board member"
```

**Map:** People who followed subject across 2+ companies. Investors who backed
them repeatedly (repeat conviction) vs. those who stopped (negative signal).
Board members across ventures. Former employees with notable outcomes.

### 3C. Graph Interpretation

| Pattern | Signal |
|---|---|
| 3+ people followed subject to new company | Strong talent magnetism |
| Same lead investor across 2+ companies | Repeat conviction from informed party |
| Co-founder from previous venture returns | Deep trust, proven working relationship |
| Key executives left within 12 months | Possible leadership/culture problem |
| No repeat relationships across ventures | May indicate bridge-burning |
| Former employees started competing companies | Subject may have created talent, or driven talent away |

---

## Phase 4: Synthesis — Final Output

### 4A. Person Profile

```
Name:           [FULL NAME]
Current Role:   [TITLE] at [COMPANY] (since [DATE])
Location:       [CITY, COUNTRY]
Education:      [DEGREE, INSTITUTION, YEAR] [SELF-REPORTED / VERIFIED]
LinkedIn:       [URL]
Crunchbase:     [URL]
Scholar:        [URL or "N/A"]
Notable:        [One-line distinguishing fact]

Research Context: [Investment diligence / Hiring / Partnership / General]
```

### 4B. Verified Timeline

Chronological table. Every row cites source tier. Flag `[GAP]`, `[DISPUTED]`, `[MISSING]`:

| Period | Role | Company | Outcome | Source |
|---|---|---|---|---|
| 2020-present | CEO & Co-Founder | Acme Corp | Active, Series B | `[CORROBORATED]` Crunchbase |
| 2017-2020 | VP Engineering | BigCo | Left [CLAIMED voluntary] | `[SELF-REPORTED]` LinkedIn |
| 2015-2017 | Co-Founder [DISPUTED] | StartupX | Acqui-hired [DISCREPANCY] | T2 vs T3 conflict |
| 2013-2015 | [GAP] | Unknown | — | `[MISSING]` |

### 4C. Outcomes Ledger

Every venture the subject led/co-founded. Columns: Company, Role Claimed,
Verified Role, Outcome Claimed, Verified Outcome, Source. Tag discrepancies
between claimed and verified. If no verifiable exits: flag as unusual for
anyone claiming 10+ years of entrepreneurship.

### 4D. Social Graph Summary

List recurring nodes (people who followed subject across ventures), repeat
investors, and notable absences (co-founders who did NOT follow). Include
talent portability count: "[X] people across [Y] ventures."

### 4E. Narrative Discrepancies (MANDATORY TABLE)

| # | Claim (Source) | Counter-Evidence (Source) | Severity | Question |
|---|---|---|---|---|
| 1 | "Co-Founder" `[T3]` LinkedIn | "Head of Eng" `[T2]` Crunchbase | HIGH | "What was your initial role at StartupX?" |
| 2 | "Acquired" `[T3]` LinkedIn | "Acqui-hire; product shut down" `[T2]` TechCrunch | MEDIUM | "Walk me through the exit structure." |
| 3 | No ProjectY on LinkedIn `[OMISSION]` | Crunchbase: Founder 2016-17 `[T2]` | HIGH | "Tell me about ProjectY." |

*If none: "No discrepancies across [N] sources. Clean record or insufficient
source diversity. Backchannel recommended."*

### 4F. Red Flags & Missing Data

Table: Flag, Type (Legal/Omission/Context), Detail, Severity (HIGH/MED/LOW).
Always tag lawsuits as `[ALLEGED]`. Tag marketing awards as `[SYNTHETIC CREDIBILITY]`.

### 4G. Diligence Questions (Generated from Discrepancies)

Organized by priority for backchannel calls, interviews, or reference checks:

```
PRIORITY 1 — Address Discrepancies:
  "LinkedIn lists co-founder; Crunchbase says Head of Eng. Clarify role?"
  "Gap 2013-2015 — what were you working on?"

PRIORITY 2 — Verify Outcomes:
  "Walk through the StartupX exit — full acquisition or acqui-hire?"
  "What happened to ProjectY after 2017?"

PRIORITY 3 — Probe Social Graph:
  "Co-founder [C] didn't join your next company. Why the split?"

PRIORITY 4 — Backchannel Targets:
  Contact [PERSON A] — followed subject across ventures. Confirm depth.
  Contact [PERSON C] — did NOT follow. May provide counter-narrative.
  Contact [INVESTOR B] — repeat backer. "What made you re-invest?"
```

### 4H. Sources

Grouped by tier: T1 Regulatory (SEC, patents, courts), T2 Databases (Crunchbase,
Bloomberg, Scholar), T3 Self-Reported (LinkedIn, Twitter, Forbes), Shadow Data
(Reddit, HN, Glassdoor, Blind), Media (news, podcasts, talks). All URLs cited.

---

## Anti-Patterns (DO NOT)

| Anti-Pattern | Why It Fails |
|---|---|
| Producing a "credibility score" or risk rating | False precision from noisy, incomplete data. The human decides. |
| Computing "Career Velocity" | Penalizes long-term builders (velocity = 0), rewards job-hoppers |
| Treating lawsuits as facts | Court filings are allegations. Settlements are not admissions of guilt. |
| Averaging conflicting data | Destroys the signal. Surface both claims with sources. |
| Penalizing low social media presence | Deep-tech founders, quants, and operators are often quiet online |
| Treating Forbes 30U30 / TEDx as competence signals | These are marketing achievements, not operational proof |
| Dumping raw transcripts into context | Triggers "lost in the middle" degradation. Summarize first. |
| Skipping disambiguation for common names | Poisons entire context window. Irrecoverable once wrong person is loaded. |
| Searching for private PII (address, SSN, medical) | Violates safety policy and adds zero professional diligence value |
| Declaring a verdict on the person | The skill surfaces data and friction. The human makes the judgment call. |
| Treating Crunchbase as ground truth | Profiles are self-editable. Funding amounts can be gamed. |
| Ignoring what is missing | The most dangerous red flags are actively scrubbed from the internet |

---

## Structural Limitations (Include in Every Output)

Always append: (1) Public data only — backchannel conversations are inaccessible,
(2) LinkedIn/Crunchbase/Bloomberg may restrict access, (3) SEC 13D/13G = public
companies only, (4) This maps friction, not truth — human verification required,
(5) Non-US subjects may have sparser data; absence is not evidence.

---

## Integration with Sister Skills

When invoked standalone, produce the full output above. When invoked from
`/due-diligence`, pass results back with a hypothesis-driven summary:

```
PERSON RESEARCH SUMMARY for [NAME] (invoked from /due-diligence):
- KEY FINDING: [Most significant discrepancy or social graph signal]
- CONFIDENCE: [HIGH/MEDIUM/LOW] — based on source diversity
- DISCREPANCIES: [count] found across [N] sources
- RECOMMENDED: [Specific backchannel target and question]
```

---

## Example Invocations

```
"who is Dario Amodei"
  -> Unique name. Full pipeline. Map OpenAI->Anthropic co-founder exodus.

"founder research on John Chen at Acme Corp"
  -> Common name, company anchor provided. Proceed with full pipeline.

"background on the GP — Sarah Miller"
  -> Ambiguous. HALT. Ask for fund name, location, or time period.

"research [person]" (from /due-diligence)
  -> Full pipeline, return compressed summary for integration.
```

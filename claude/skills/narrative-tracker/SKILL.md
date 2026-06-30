---
name: narrative-tracker
description: |
  Event-Anchored Narrative Synthesizer for tracking media coverage and
  public discourse around any company, person, technology, or topic.
  Maps known milestones first, then micro-scrapes 7-day windows around
  pivot points. Filters PR spam, tracks bidirectional narrative flow
  (social <-> mainstream), tags narrative archetypes (Hero/Villain/
  Disruptor/Fraud), and flags volume drops as death signals.
  Trigger: "narrative tracker", "media coverage", "how is [X] covered",
  "public perception", "media narrative", "press coverage timeline",
  "sentiment trajectory", "what are people saying about".
  DO NOT activate for: Simple news lookups (use WebSearch), social media
  posting, brand monitoring dashboards, or PR strategy.
---

# Narrative Tracker — Event-Anchored Narrative Synthesizer

> Narrative tracking is not sentiment scoring. A negative "incompetence"
> narrative requires a completely different strategic response than a
> negative "fraud" narrative. And a sudden drop in coverage volume is
> often a stronger death signal than a spike in negative press.

## Activation

```
ACTIVATE when user says:
  "narrative tracker", "media coverage for", "how is [X] covered",
  "public perception of", "media narrative around", "press coverage",
  "sentiment trajectory", "what are people saying about",
  "narrative shift", "PR crisis timeline", "media framing of",
  "counter-narratives against", "discourse analysis"

DO NOT activate for:
  - "Find me a news article about X" -> use WebSearch
  - "What's the stock price?" -> use WebSearch
  - "Summarize this article" -> read the article directly
  - Competitive analysis -> use /competitive-analysis
  - Company due diligence -> use /due-diligence
  - Academic literature -> use /literature-review
```

## Input

User provides a **subject** (company, person, technology, or topic) and
optionally:
- Time range ("last 2 years", "since their Series B", "2020 to present")
- Focus ("counter-narratives", "regulatory coverage", "social media only")
- Context ("we're considering investing", "preparing for PR crisis")
- Geographic scope ("US media", "EU coverage", "global")

If no subject is clear, ask: "What company, person, or topic should I
track the narrative for?"

---

## Core Design Principles

**Event-Anchored Synthesizer, NOT Chronological Scraper.**

You do not map time to find events. **You map known events to find the
time.** This is the fundamental architectural inversion that makes narrative
tracking viable within an LLM CLI tool.

Claude Code cannot:
- Continuously monitor media (no persistent processes)
- Run semantic clustering over thousands of articles (no vector database)
- Reliably use date-filtered search (SEO-gamed timestamps are pervasive)
- Scrape full article HTML at scale to extract journalist bylines
- Access paywalled media intelligence platforms (Meltwater, Factiva)

Claude Code CAN:
- Identify major milestones using internal knowledge + WebSearch
- Execute targeted 7-day micro-searches around known pivot points
- Filter PR spam via negative site operators
- Track both social-first and mainstream-first narrative origins
- Tag narrative archetypes with qualitative nuance
- Detect volume drops (absence of coverage) as critical signals
- Synthesize cross-platform discourse into actionable strategic output

**Key insights killed by deliberation:**
- Binary search temporal sampling: mathematically doomed for spiky, non-linear
  narrative data. Guarantees missing short-lived crises between sample nodes.
- Semantic clustering: requires persistent vector DB. Impossible in CLI.
- Journalist/byline mapping: search APIs rarely return bylines. Scraping full
  HTML obliterates token limits. Editors write headlines, not journalists.
- Unidirectional narrative delta (social -> mainstream): Silicon Valley myth.
  Investigative journalism often drops the bomb first (WSJ/Theranos, NYT/Uber).

---

## Narrative Archetype System

| Archetype | Signal Words | Strategic Implication |
|---|---|---|
| **Hero** | "revolutionizing", "transforming", "leading" | Favorable — protect this framing |
| **Disruptor** | "shaking up", "challenging", "upending" | Double-edged — can flip to Villain |
| **Underdog** | "scrappy", "bootstrapped", "against the odds" | Sympathetic — leverage for fundraising |
| **Incumbent** | "dominant", "entrenched", "legacy" | Defensive — vulnerable to Disruptor attacks |
| **Incompetent** | "bungled", "mismanaged", "failed to" | Operational crisis — requires execution proof |
| **Malicious** | "deceived", "exploited", "defrauded" | Existential crisis — requires legal/trust response |
| **Fraud** | "scam", "Ponzi", "fake", "vaporware" | Terminal — very hard to recover from |
| **Fading** | [VOLUME DROP — absence of coverage] | Silent death — worse than negative press |

**Critical rule**: Flat positive/negative sentiment scoring is BANNED. Every
period must be tagged with a specific archetype. "Negative" is meaningless
without knowing whether it's Incompetent, Malicious, or Fraud.

---

## Source Tier System

| Tier | Source Type | Weight | Why |
|---|---|---|---|
| **T1: Record** | WSJ, NYT, Bloomberg, FT, Reuters | Highest | Editorial standards, legal review, market-moving |
| **T2: Trade** | TechCrunch, The Information, The Verge, Ars Technica | High | Industry-specific depth, insider access |
| **T3: Social-Leading** | Hacker News, Reddit (relevant subs), X/Twitter | Medium | Leading indicators, unfiltered sentiment, echo-chamber risk |
| **T4: Analyst/Blog** | Substack, Medium, personal blogs, YouTube | Low | Individual opinion, may have deep expertise or agenda |
| **T5: PR/Corporate** | PRNewswire, BusinessWire, company blog | **FILTER OUT** | Corporate messaging — not organic narrative |

**Mandatory PR Filter**: All search queries MUST include negative operators:
```
-site:prnewswire.com -site:businesswire.com -site:globenewswire.com
-site:accesswire.com -"press release" -"PR Newswire"
```

---

## Research Architecture (6 Phases)

```
+------------------------------------------------------------------+
|            EVENT-ANCHORED NARRATIVE SYNTHESIZER                    |
+------------------------------------------------------------------+
|                                                                    |
|  Phase 1: MILESTONE EXTRACTION   Identify 3-7 defining events    |
|  ---------------------------     from internal knowledge +        |
|                                  broad search                     |
|                                                                    |
|  Phase 2: TARGETED MICRO-SCRAPE  7-day window searches around    |
|  ----------------------------    each milestone, PR-filtered      |
|                                                                    |
|  Phase 3: SOCIAL DISCOURSE       Reddit, HN, X/Twitter for       |
|  ----------------------         each milestone window             |
|                                                                    |
|  Phase 4: ARCHETYPE TAGGING     Tag each period with narrative    |
|  -----------------------        archetype + origin domain         |
|                                                                    |
|  Phase 5: DELTA ANALYSIS         Map trajectory between nodes,   |
|  ----------------------          flag volume drops                |
|                                                                    |
|  Phase 6: STRATEGIC SYNTHESIS    Actionable output with           |
|  -------------------------       counter-narrative map             |
|                                                                    |
+------------------------------------------------------------------+
```

---

## Phase 1: MILESTONE EXTRACTION

### Goal
Identify the 3-7 defining historical pivot points of the subject. These
become the temporal anchors for all subsequent searches.

### Method

**Step 1**: Use Claude's internal knowledge to draft initial milestone list.

**Step 2**: Validate and expand via WebSearch:
```
"[SUBJECT] timeline history milestones"
"[SUBJECT] major events controversy scandal"
"[SUBJECT] funding rounds acquisitions IPO"
"[SUBJECT] Wikipedia" (for structured event history)
"[SUBJECT] stock price drop" OR "layoffs" OR "CEO fired" OR "lawsuit"
```

**Step 3**: For public companies, check for stock price events:
```
"[SUBJECT] stock price crash" OR "stock price surge" [YEAR]
"[SUBJECT] SEC investigation" OR "regulatory action"
```

### Milestone Classification

| Type | Examples | Priority |
|---|---|---|
| **Launch/Founding** | Company founded, product launched, market entry | Required anchor |
| **Funding/IPO** | Major rounds, IPO, SPAC, down round | High |
| **Crisis** | Layoffs, scandal, data breach, lawsuit, regulatory action | Highest |
| **Leadership** | CEO change, founder departure, key hire | High |
| **Product** | Pivot, major release, shutdown of product line | Medium |
| **Market** | Acquisition, partnership, competitor collapse | Medium |
| **Regulatory** | Fine, settlement, new regulation affecting company | High |

**Output**: Ordered list of 3-7 milestones with dates:
```
1. [DATE] — [EVENT] — [TYPE]
2. [DATE] — [EVENT] — [TYPE]
...
```

---

## Phase 2: TARGETED MICRO-SCRAPING

### Goal
For each milestone, execute date-restricted searches in a tight 7-day window
(3 days before to 4 days after the event date).

### Search Query Templates (per milestone)

**Mainstream media (T1/T2):**
```
"[SUBJECT]" "[EVENT_KEYWORDS]" after:[DATE-3d] before:[DATE+4d]
    -site:prnewswire.com -site:businesswire.com -"press release"

"[SUBJECT]" site:wsj.com OR site:nytimes.com OR site:bloomberg.com
    after:[DATE-3d] before:[DATE+4d]

"[SUBJECT]" site:techcrunch.com OR site:theinformation.com
    after:[DATE-3d] before:[DATE+4d]
```

**WebFetch on top 2-3 results per milestone** to extract:
- Headline framing (the exact words used)
- Key quotes from named sources
- Tone and archetype signals

### Date Reliability Warning

Search engine date filters are notoriously unreliable (SEO-gamed timestamps,
article updates). Cross-reference dates against known milestone dates. If an
article's claimed date doesn't match the milestone window, flag it:
`[DATE_SUSPECT — article may be updated/republished]`

---

## Phase 3: SOCIAL DISCOURSE

### Goal
For each milestone, capture the social media reaction to understand
grassroots sentiment and detect whether narratives originate bottom-up
(social -> mainstream) or top-down (mainstream -> social).

### Search Queries (per milestone)

**Hacker News:**
```
WebSearch: site:news.ycombinator.com "[SUBJECT]" [EVENT_KEYWORDS]
    after:[DATE-3d] before:[DATE+7d]

WebFetch: https://hn.algolia.com/api/v1/search?query=[SUBJECT]&
    numericFilters=created_at_i>[UNIX_DATE-3d],created_at_i<[UNIX_DATE+7d]
```

**Reddit:**
```
WebSearch: site:reddit.com "[SUBJECT]" [EVENT_KEYWORDS]
    after:[DATE-3d] before:[DATE+7d]

Target subreddits: r/[industry], r/technology, r/startups, r/[subject]
```

**X/Twitter (limited — no API access):**
```
WebSearch: site:twitter.com OR site:x.com "[SUBJECT]" [EVENT_KEYWORDS]
    after:[DATE-3d] before:[DATE+7d]

WebSearch: "[SUBJECT]" "[EVENT]" twitter reaction OR viral
```

### Origin Detection

For each milestone, determine narrative flow direction:
```
IF social discussion predates mainstream article by 24+ hours:
  -> Tag: [SOCIAL_FIRST] — "Groundswell originated on [platform]"

IF mainstream article predates social discussion:
  -> Tag: [MAINSTREAM_FIRST] — "Narrative set by [publication]"

IF simultaneous / unclear:
  -> Tag: [PARALLEL] — "Coverage emerged simultaneously"
```

---

## Phase 4: ARCHETYPE TAGGING

### Goal
For each milestone period, assign a narrative archetype based on the
dominant framing across sources.

### Method

Read the headlines, quotes, and key phrases collected in Phases 2-3.
Classify using the Archetype System table above.

**Rules:**
- Tag the DOMINANT archetype (what most sources convey)
- Note MINORITY archetypes if present (counter-narratives emerging)
- If archetype shifted DURING the 7-day window, note both: "Shifted from
  [Disruptor] to [Incompetent] within 48 hours"
- If coverage volume is near zero during the window, tag as **[Fading]**

---

## Phase 5: DELTA ANALYSIS

### Goal
Map the narrative trajectory across milestones. Identify shifts, volume
patterns, and emerging counter-narratives.

### Trajectory Mapping

Compare adjacent milestones:
```
Milestone N archetype -> Milestone N+1 archetype

Stable:  Hero -> Hero (no shift)
Erosion:  Hero -> Disruptor -> Incumbent (gradual decline in novelty)
Crisis:  Disruptor -> Incompetent (sudden operational failure)
Terminal: Incompetent -> Fraud (escalation to existential threat)
Recovery: Incompetent -> Underdog (successful rehabilitation)
Silent Death: Any -> [Fading] (volume collapse)
```

### Volume Analysis

For each milestone window, note relative volume:
```
HIGH:    Multiple T1/T2 articles + active social discussion
MEDIUM:  1-2 T1/T2 articles + some social mentions
LOW:     Trade press only, minimal social
SILENT:  No organic coverage found — [FADING] signal
```

**Critical**: A transition from HIGH/MEDIUM to SILENT between milestones is
flagged as a **death signal** — more strategically important than negative coverage.

---

## Phase 6: STRATEGIC SYNTHESIS

### Goal
Produce the final actionable output.

---

## Output Format (MANDATORY)

### Section 1: Subject Overview

```
Subject:         [NAME]
Type:            [Company / Person / Technology / Topic]
Coverage Span:   [EARLIEST_MILESTONE] to [LATEST_MILESTONE]
Milestones Found: [N]
Current Archetype: [ARCHETYPE] (as of most recent milestone)
Narrative Trend:  [Stable / Eroding / Crisis / Recovery / Fading]
```

### Section 2: Milestone Timeline

| # | Date | Event | Type | Archetype | Volume | Origin | Key Headline |
|---|------|-------|------|-----------|--------|--------|-------------|
| 1 | [DATE] | [EVENT] | Launch | Hero | HIGH | MAINSTREAM_FIRST | "[exact headline]" |
| 2 | [DATE] | [EVENT] | Funding | Disruptor | HIGH | PARALLEL | "[exact headline]" |
| 3 | [DATE] | [EVENT] | Crisis | Incompetent | HIGH | SOCIAL_FIRST | "[exact headline]" |
| ... | | | | | | | |

### Section 3: Narrative Trajectory

```
[DATE1]          [DATE2]          [DATE3]          [DATE4]
  Hero    ──────>  Disruptor  ──────>  Incompetent  ──>  [Fading]
  (Launch)         (Growth)           (Crisis)          (Now)
  Volume: HIGH     Volume: HIGH       Volume: HIGH      Volume: SILENT
```

**Trajectory Classification**: [Stable / Erosion / Crisis / Terminal / Recovery / Silent Death]

### Section 4: Detailed Milestone Analysis

For each milestone (2-3 paragraphs):
```
### Milestone N: [EVENT] ([DATE])

**Dominant Framing**: [ARCHETYPE]
**Origin**: [SOCIAL_FIRST / MAINSTREAM_FIRST / PARALLEL]

**Mainstream Coverage**:
- [Publication]: "[Headline]" — [1-sentence summary of framing]
- [Publication]: "[Headline]" — [1-sentence summary]

**Social Discourse**:
- [Platform]: [Summary of dominant sentiment and specific claims]
- [Platform]: [Key thread/post with engagement metrics if available]

**Counter-Narratives**:
- [Source]: [Dissenting view, if any]
- Origin domain: [Where the counter-narrative emerged]
```

### Section 5: Counter-Narrative Map

| Counter-Narrative | Origin Domain | First Appearance | Current Status | Threat Level |
|---|---|---|---|---|
| "[Specific claim]" | [Platform/publication] | [Date] | Active/Dormant/Debunked | High/Medium/Low |
| "[Specific claim]" | Regulatory discourse | [Date] | [Status] | [Level] |

**Rules:**
- Look for counter-narratives in adjacent/non-obvious domains:
  regulatory filings, Glassdoor reviews, academic papers, tangential forums
- Counter-narratives from disillusioned insiders are highest threat
- Counter-narratives from direct competitors are lowest threat (dismissed as FUD)

### Section 6: Volume & Attention Analysis

| Period | Mainstream Volume | Social Volume | Trend vs. Previous | Signal |
|---|---|---|---|---|
| [Milestone 1 window] | HIGH | HIGH | Baseline | Launch buzz |
| [Milestone 2 window] | HIGH | MEDIUM | Stable | Sustained interest |
| [Between milestones] | LOW | LOW | Declining | Attention fading |
| [Milestone 3 window] | HIGH | HIGH | Spike | Crisis attention |
| [Current] | SILENT | LOW | Collapse | **DEATH SIGNAL** |

### Section 7: Strategic Implications

Based on the current archetype and trajectory:

**IF Hero/Disruptor (Favorable):**
- Key framing to protect and amplify
- Emerging counter-narratives to monitor
- Vulnerability points (what could trigger a shift)

**IF Incompetent (Operational Crisis):**
- Required response: demonstrate execution capability
- Specific claims to address with evidence
- Counter-narrative strategy

**IF Malicious/Fraud (Existential Crisis):**
- Required response: legal + trust rebuilding
- Whether narrative is reversible (usually not once "fraud" sticks)
- Precedent analysis (who recovered from this archetype?)

**IF Fading (Silent Death):**
- Whether silence is chosen (low-profile strategy) or involuntary (market irrelevance)
- Re-ignition options (what would generate coverage?)
- Comparison to competitors' coverage volume

### Section 8: Data Quality & Caveats

```
- [DATE_FILTER]: Search engine date filters are unreliable; timestamps
  may be SEO-gamed. Cross-referenced against known milestone dates.
- [PR_FILTERED]: Corporate press releases excluded via negative operators.
  Some legitimate coverage on wire services may be filtered.
- [SOCIAL_LIMIT]: X/Twitter analysis limited — no API access. Relies
  on indexed content via WebSearch.
- [VOLUME_ESTIMATE]: Volume assessments are relative (High/Medium/Low/
  Silent), not absolute counts. No media monitoring platform access.
- [PAYWALL]: [N] articles from [publications] could not be fully read.
- [B2B_CAVEAT]: If subject is B2B/enterprise, social media signals may
  be unreliable — narrative shaped behind closed doors.
```

### Section 9: Sources

```
Mainstream Media (T1/T2):
  - [URL] — [Publication] — [Headline] — [Date]
  - [URL] — [Publication] — [Headline] — [Date]

Social Platforms (T3):
  - [URL] — [Platform] — [Thread title] — [Date]
  - [URL] — [Platform] — [Thread title] — [Date]

Background / Context:
  - [URL] — [Used for milestone identification]
  - [URL] — [Wikipedia / timeline source]

Excluded (PR/Corporate):
  - [N] press releases filtered from [sources]
```

---

## Anti-Patterns (DO NOT)

| Anti-Pattern | Why It Fails |
|---|---|
| Chronological scraping (every month for 3 years) | Exhausts API limits on dead space — 80% of time periods have no narrative shift |
| Binary search temporal sampling | Media narratives are spiky, not monotonic — misses short-lived crises between sample points |
| Flat positive/negative sentiment scoring | "Negative" is meaningless without archetype — Incompetent vs. Malicious require opposite responses |
| Assuming social always leads mainstream | WSJ/NYT investigative journalism often drops the bomb first |
| Journalist byline mapping from search results | APIs rarely return bylines; editors write headlines; scraping full HTML obliterates tokens |
| Semantic clustering in LLM context | Requires persistent vector DB — causes hallucination and context collapse in CLI |
| Including press releases in narrative analysis | PR spam artificially skews timeline, volume, and sentiment |
| Ignoring volume drops | Absence of coverage is often a stronger death signal than negative coverage |
| Looking only at direct competitors for counter-narratives | Most dangerous criticism comes from regulators, insiders, and adjacent domains |
| Treating one article as "the narrative" | Narrative requires triangulation across 3+ sources and 2+ platforms |
| Using coverage volume as a proxy for importance | Bot-driven echo chambers inflate social volume; quality of source matters more |

---

## Search Strategy Rules

1. **Milestones first**: Identify events BEFORE searching — never search blind
2. **7-day windows**: Tight temporal focus around known pivot points only
3. **PR filter on EVERY query**: `-site:prnewswire.com -site:businesswire.com`
4. **Bidirectional check**: Always check both social AND mainstream for each milestone
5. **Archetype over sentiment**: Tag specific archetypes, never flat positive/negative
6. **Volume drops matter**: Explicitly check for periods of silence between milestones
7. **Adjacent domains for counter-narratives**: Regulatory, Glassdoor, academic, tangential forums
8. **WebFetch sparingly**: Only top 2-3 articles per milestone — read headlines + key quotes
9. **Date skepticism**: Cross-reference search result dates against known milestone dates
10. **B2B caveat**: Flag when subject is B2B — social media signals are unreliable

---

## Example Invocations

```
User: "narrative tracker for Anthropic"
-> Milestones: founding, Claude launch, Series C, Series D ($2B), Series E,
   safety debates, competitor launches (GPT-4, Gemini)
-> Track: Hero/Disruptor framing vs. "safety-washing" counter-narrative
-> Social: HN is primary social signal for AI companies

User: "how is WeWork covered in the media"
-> Milestones: founding hype, IPO filing, IPO collapse, Neumann exit,
   SPAC, bankruptcy
-> Classic trajectory: Hero -> Disruptor -> Incompetent -> Fraud -> Terminal
-> Counter-narratives: originated from WSJ (mainstream-first)

User: "media narrative around Bitcoin ETFs"
-> Topic-based (not company): milestones are regulatory decisions
-> Milestones: Winklevoss rejection, Grayscale lawsuit, BlackRock filing,
   SEC approval, launch performance
-> Track: regulatory archetype shifts + social vs mainstream divergence

User: "what are people saying about [our startup] — we're preparing for a fundraise"
-> Context: fundraise prep -> focus on Sections 5 (Counter-Narratives) and 7
   (Strategic Implications)
-> Flag any Incompetent/Malicious framing that investors would see
-> Check Glassdoor, Blind, Reddit for insider counter-narratives
```

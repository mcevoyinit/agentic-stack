---
name: literature-review
description: |
  Seed-and-Expand Interactive Recommender for academic literature surveys.
  User provides 1-3 seed papers; Claude maps the citation neighborhood via
  Semantic Scholar API, writes local Python (NetworkX) to prune the graph,
  presents branches, and lets the user choose which lineage to deep-dive.
  Field-adaptive output: Methodology Matrix (empirical), Theorem Lineage
  (theoretical), or Conceptual Frameworks (qualitative).
  Trigger: "literature review", "academic survey", "research papers on",
  "state of the art", "what papers exist on", "prior research on",
  "scholarly review".
  DO NOT activate for: Simple fact lookups, single-paper summaries,
  homework help, or generating fake citations.
---

# Literature Review Skill

> A literature review is a graph traversal problem, not a summarization
> problem. You must map the edges (who cites whom) BEFORE you read the
> nodes (abstracts). Abstracts are marketing documents — limitations and
> real gaps live in Conclusions sections and in papers published one year
> later. The agent's job is to build the citation graph, let the human
> steer, and then extract from full texts where available.

## Activation

```
ACTIVATE when user says:
  "literature review", "academic survey", "research papers on",
  "state of the art", "what papers exist on", "prior research on",
  "scholarly review", "systematic review of", "citation graph for",
  "who cites [paper]", "what's the research landscape on"

DO NOT activate for:
  - Single paper summary → just read and summarize directly
  - Homework questions → refuse or answer directly
  - Generating fake/hallucinated citations → refuse absolutely
  - Simple fact lookups → use WebSearch directly
```

## Input

User provides a **research topic** (required) and optionally:
- 1 to 3 **seed papers** (DOIs, titles, or Semantic Scholar IDs)
- Focus constraint ("just the methodology comparison" or "gaps only")
- Field hint ("this is theoretical mathematics" or "empirical ML")
- Time window ("papers since 2020")

If no seed papers are provided, ask:
> "Do you have 1-3 papers you already know are relevant? Seed papers
> dramatically improve the quality of the citation graph. If not, I'll
> start with a keyword search and survey-paper hunt."

---

## Core Design Principles

**Seed-and-Expand Interactive Recommender, NOT Autonomous Batch-Processor.**

The skill does NOT autonomously decide what is "seminal" or "important."
It builds the citation neighborhood of user-provided seeds, presents
branches, and lets the human choose which lineage to explore. The LLM
is a research assistant, not an omniscient oracle.

**What Claude Code CAN do:**
- Query the Semantic Scholar Graph API for citation networks and metadata
- Write and execute local Python (NetworkX) to compute graph structure
- Fetch open-access full texts from arXiv and PubMed Central
- Extract Conclusions/Limitations sections from OA papers
- Synthesize structured, field-adaptive research summaries
- Map authors and institutions from API metadata

**What Claude Code CANNOT do:**
- Access paywalled full texts (Elsevier, Springer, IEEE behind paywall)
- Determine scientific validity from metadata alone
- Reliably reconstruct paywalled methodology from citing contexts
- Separate genius preprints from crank submissions without human judgment
- Query Google Scholar (CAPTCHAs, no API, aggressive rate-limiting)

---

## Grounding Rules (MANDATORY — Zero Tolerance)

| Rule | Rationale |
|------|-----------|
| NEVER mention a paper not returned by Semantic Scholar API or WebSearch | LLMs hallucinate plausible-sounding papers. Every citation must trace to an API response |
| ALWAYS cite as `[Author, Year]` linked to Semantic Scholar URL or DOI | Verifiable provenance for every claim |
| NEVER generate fake DOIs, Semantic Scholar IDs, or arXiv IDs | Fabricated identifiers are worse than no citation |
| NEVER claim to have read a paywalled paper's methodology | If no OA full text exists, mark as "Metadata Only" |
| NEVER use Google Scholar programmatically | CAPTCHAs will break the workflow silently |
| ALWAYS separate API-grounded facts from LLM synthesis | Use explicit markers: `[FROM API]` vs `[SYNTHESIZED]` |

---

## The "Abstracts Lie" Principle

Abstracts are marketing documents. They highlight successes and hide
limitations. When synthesizing the State of the Art:

1. **DO NOT** rely on abstracts for gap analysis or limitation mapping
2. **DO** extract from Conclusions, Future Work, and Limitations sections
   of open-access full texts
3. **DO** check the Introductions of papers published 1-2 years AFTER
   the target paper — they often explicitly state what the earlier work
   got wrong
4. If only the abstract is available (paywalled), mark the synthesis as
   `[ABSTRACT-ONLY — limitations may be understated]`

---

## Survey Paper Shortcut (with Bias Warning)

The single highest-ROI action when entering a new domain is to find
recent survey papers. Execute this BEFORE building the citation graph:

```
Semantic Scholar query:
  "[Topic]" AND ("survey" OR "review" OR "systematic review")
  Filter: year >= (current_year - 3)
  Sort: citationCount descending
  Limit: 5 results
```

**MANDATORY WARNING to user when using survey papers:**
> "I found [N] recent survey papers. Using these as a scaffold saves
> significant computation, but be aware: relying on any single survey
> inherits its authors' specific biases, blind spots, and framing.
> I will cross-reference across surveys where possible."

If a recent OA survey exists, fetch its full text and use its taxonomy
as the initial branch structure — but always validate branches against
the raw citation graph.

---

## Research Architecture (5 Phases)

```
┌──────────────────────────────────────────────────────────────────┐
│                 LITERATURE REVIEW: SEED-AND-EXPAND               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: INITIALIZATION       Get seeds, write Python graph     │
│  ─────────────────────         script, install deps if needed    │
│                                                                  │
│  Phase 2: GRAPH RETRIEVAL      Semantic Scholar API + NetworkX   │
│  ────────────────────          citation graph + survey hunt      │
│                                                                  │
│  Phase 3: HUMAN PIVOT          Present branches, user chooses    │
│  ────────────────────          which lineage to explore          │
│                                                                  │
│  Phase 4: TARGETED EXTRACTION  Fetch OA full texts for chosen    │
│  ────────────────────────────  branch, read Conclusions/Limits   │
│                                                                  │
│  Phase 5: SYNTHESIS            Field-adaptive structured output  │
│  ──────────────────            with full provenance chain        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: INITIALIZATION

### Goal
Collect seed papers, classify the field, and scaffold the local Python
environment for graph computation.

### Steps

1. **Collect seeds**: Ask user for 1-3 seed papers. Accept DOIs, titles,
   arXiv IDs, or Semantic Scholar paper IDs.

2. **Resolve seeds via API**: For each seed, run a Semantic Scholar
   search to confirm it exists and retrieve the canonical paper ID.
   ```
   WebFetch: https://api.semanticscholar.org/graph/v1/paper/search?query={title}&limit=5&fields=paperId,title,year,authors,citationCount,influentialCitationCount,isOpenAccess,openAccessPdf
   ```
   If the user provides a DOI: `https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=...`

3. **Classify the field**: From the seed papers' venues and abstracts,
   determine the epistemological category:
   - **Empirical** (ML, medicine, social science with data) → Methodology Matrix output
   - **Theoretical** (mathematics, theoretical physics, formal CS) → Theorem Lineage output
   - **Qualitative** (humanities, qualitative sociology, law) → Conceptual Frameworks output
   - **Mixed** → ask the user which lens to apply

4. **Write the graph script**: Create a temporary Python script at
   `/tmp/lit_review_graph.py` that uses `requests` and `networkx`.
   Install dependencies if missing:
   ```bash
   pip install networkx requests 2>/dev/null || pip3 install networkx requests
   ```

### Semantic Scholar API Reference

```
Base URL: https://api.semanticscholar.org/graph/v1

Paper search:     GET /paper/search?query={q}&limit=100&fields={fields}
Paper by ID:      GET /paper/{paper_id}?fields={fields}
Paper citations:  GET /paper/{paper_id}/citations?limit=500&fields={fields}
Paper references: GET /paper/{paper_id}/references?limit=500&fields={fields}

Useful fields:
  paperId, title, year, authors, abstract, venue, citationCount,
  influentialCitationCount, isOpenAccess, openAccessPdf, externalIds,
  tldr, fieldsOfStudy

Rate limit: 100 requests per 5 minutes (free tier)
  → Build backoff into the Python script: 1s delay between calls,
    exponential backoff on 429
```

---

## Phase 2: GRAPH RETRIEVAL & PRUNING

### Goal
Build the 1-degree citation neighborhood of all seed papers, prune it
to manageable size, and identify distinct research branches.

### The Python Graph Script

Claude MUST write and execute a local Python script for this phase.
An LLM cannot hold a 500-node citation graph in context without
hallucinating or exhausting tokens. NetworkX handles the graph math;
Claude reads only the pruned output.

**Script responsibilities:**

1. **Fetch**: For each seed, pull forward citations (papers citing it)
   and backward references (papers it cites) via S2 API
2. **Build graph**: Nodes = papers (with metadata), Edges = citations
3. **Prune**: Remove self-citations → remove zero influential citations →
   remove papers outside time window → keep top 40-60 by degree centrality
4. **Detect communities**: `greedy_modularity_communities` or Louvain →
   3-5 clusters. Label each by top-3 title keywords + anchor paper
5. **Output to stdout**: Structured markdown — raw count, pruned count,
   branches with labels, top 5 papers per branch, OA percentage
6. **Survey hunt**: Separate query for recent survey papers on the topic

### API Resilience (built into the script)

- `429 Too Many Requests` → exponential backoff (1s, 2s, 4s, 8s, max 30s)
- `404 Not Found` → skip paper, log warning
- Network timeouts → retry once after 5s
- Empty results → degrade gracefully, report to user

---

## Phase 3: THE HUMAN-IN-THE-LOOP PIVOT

### Goal
Present the detected branches to the user and let them choose which
lineage to explore. This is the critical design decision — the agent
does NOT autonomously decide what matters.

### Presentation Format

For each branch, show: auto-generated label (from title keywords), anchor
paper with citation count, total papers and OA percentage, top 3 key nodes
with influential citation counts, year range, and a 1-sentence direction
summary. End with graph stats (raw → pruned → branches) and ask:
"Which branch should I deep-dive into?"

### Rules for This Phase

- Present ALL branches, even if one seems obviously more relevant
- Do NOT pre-select or recommend a branch — let the user decide
- Show OA percentage per branch so the user knows extraction feasibility
- If the user says "all of them," warn about context window limits and
  suggest sequential processing (one branch at a time)

---

## Phase 4: TARGETED EXTRACTION

### Goal
For the user's chosen branch, fetch open-access full texts and extract
real methodology, conclusions, and limitations — NOT abstracts.

### Steps

1. **Identify OA papers in chosen branch**: From the graph output,
   filter papers where `isOpenAccess == true` and `openAccessPdf` exists.

2. **Fetch full texts**: Use WebFetch on the `openAccessPdf.url` for
   each OA paper. Hard limit: **10 papers maximum** per branch to
   avoid context exhaustion.

3. **Extract from each paper** (in this priority order):
   - **Conclusions / Discussion** section → actual findings and caveats
   - **Limitations** section → what the authors admit doesn't work
   - **Future Work** section → where the field is headed
   - **Methodology** section → only for the field-adaptive matrix
   - **Abstract** → last resort, tagged as `[ABSTRACT-ONLY]`

4. **For paywalled papers in the branch**: Record them in the
   "Paywalled Black Holes" section with metadata only. Do NOT attempt
   to reconstruct their methodology from citing contexts.

5. **Classify the field** (if not already done) and select output template:
   - **Empirical** → Methodology Matrix
   - **Theoretical** → Theorem/Proof Lineage
   - **Qualitative** → Conceptual Frameworks

### Field-Adaptive Output Templates

**Empirical (ML, Medicine, Social Science with Data):**

| Paper | Method | Dataset | Metric | Result | Limitations | OA? |
|-------|--------|---------|--------|--------|-------------|-----|
| [Author, Year] | Approach name | Dataset(s) used | Primary metric | Key number | From Conclusions | Yes/No |

**Theoretical (Math, Theoretical Physics, Formal CS):**

```
Theorem Lineage:
  [Foundational Result] (Author, Year)
    ├── [Extension 1] (Author, Year) — generalizes to [domain]
    │     └── [Further Extension] (Author, Year)
    ├── [Extension 2] (Author, Year) — alternative proof via [method]
    └── [Counterexample / Bound] (Author, Year) — shows limits of [X]
```

**Qualitative (Humanities, Law, Qualitative Sociology):**

| Paper | Framework | Lens/Theory | Key Argument | Critiques | OA? |
|-------|-----------|-------------|--------------|-----------|-----|
| [Author, Year] | Name | Theoretical tradition | Core thesis | Counter-arguments | Yes/No |

---

## Phase 5: SYNTHESIS

### Goal
Produce the final structured output with full provenance chain.

### Output Sections (ALL MANDATORY)

---

### 5A. Research Context

```
Topic:              [USER'S QUERY]
Seed Papers:        [1-3 papers with S2 links]
Field Classification: [Empirical / Theoretical / Qualitative / Mixed]
Survey Papers Used: [list, with inherited-bias warning]
Graph Stats:        [N raw → M pruned → K branches → user chose Branch X]
Date of Review:     [YYYY-MM-DD]
```

### 5B. Survey Papers Found

| Survey | Year | Scope | Citations | OA? | Inherited Bias Warning |
|--------|------|-------|-----------|-----|----------------------|
| [Title] ([Author]) | YYYY | What it covers | N | Yes/No | Key blind spot if identifiable |

### 5C. Citation Graph Branches

*From Phase 3 — reproduced here for completeness, with the chosen
branch highlighted.*

### 5D. Selected Branch Deep-Dive

**State of the Art** `[SYNTHESIZED from Conclusions sections]`
- What is considered solved in this branch
- What the current best approaches achieve
- Where consensus exists

**Field-Adaptive Comparison** (Methodology Matrix / Theorem Lineage /
Conceptual Frameworks — see Phase 4 templates)

**Gap Analysis** `[SYNTHESIZED from Limitations + Future Work sections]`
- Explicit unsolved sub-problems
- Methodological limitations acknowledged by authors
- Contradictions between papers in this branch
- Missing datasets, benchmarks, or theoretical tools

### 5E. Key Authors & Labs

| Author | Affiliation | Papers in Graph | Role | S2 Profile |
|--------|-------------|-----------------|------|------------|
| Name | Institution | N | Brief description of contribution | Link |

**Note on author mapping:** Author names are taken directly from
Semantic Scholar metadata. Name disambiguation is imperfect — authors
with common names (e.g., "Wei Li") may be conflated. Verify via S2
profile links.

**Note on authorship conventions:** Author ordering conventions vary by
field (last-author = PI in biomedicine, alphabetical in economics/math,
first-author = PI in some fields). This table does NOT infer lab
leadership from author position.

### 5F. Open Questions

Bulleted list of unresolved research questions identified from:
- Gap analysis (5D)
- Future Work sections of OA papers
- Contradictions between papers
- Areas where the citation graph shows sparse edges (under-explored connections)

### 5G. Paywalled Black Holes

Papers that appear structurally important in the citation graph but
whose full text could not be accessed.

| Paper | Year | Citations | Influential Cites | Why It Matters | What We Know |
|-------|------|-----------|-------------------|----------------|--------------|
| [Title] | YYYY | N | N | Graph centrality / cited by key papers | Metadata + abstract only |

**Disclaimer**: Methodology and limitations for these papers are
UNKNOWN. Do not assume the abstract tells the full story.

### 5H. Sources with Semantic Scholar IDs

List ALL papers referenced with format:
`[S2:ID] Author et al. (Year). "Title." Venue. DOI. [OA/PAYWALLED]`

Also list: API queries executed (search terms, result counts),
survey papers consulted separately.

---

## Search Strategy Rules

1. **Semantic Scholar is the backbone**: ALL citation data, metadata,
   and paper discovery goes through the S2 API. No Google Scholar.
2. **WebSearch for context only**: Use WebSearch to find blog posts,
   tutorials, or news ABOUT papers — never as the primary paper source.
3. **arXiv and PubMed for full text**: When S2 indicates a paper is OA,
   fetch the full text via arXiv or PubMed Central URLs.
4. **Rate limit discipline**: 1.1 seconds between S2 API calls. All
   fetching happens in the Python script, not in serial LLM tool calls.
5. **Recency**: When no time window is specified, default to the last
   5 years for frontier papers, no limit for seminal works.
6. **Depth on gaps**: For any branch with <3 OA papers, explicitly warn
   the user that the synthesis is metadata-limited.

---

## Anti-Patterns (DO NOT)

| Anti-Pattern | Why It Fails |
|---|---|
| Hallucinating paper titles or authors | The #1 failure mode of LLM lit reviews. Every paper MUST come from API data |
| Using Google Scholar programmatically | CAPTCHAs will silently return garbage or block entirely |
| Holding the raw citation graph in LLM context | 500 nodes in context → hallucinated edges and fabricated metrics. Use NetworkX |
| Treating abstracts as ground truth for SOTA | Abstracts are marketing. Conclusions and Limitations tell the real story |
| Reconstructing paywalled methodology from citing contexts | Downstream papers cite claims and baselines, not hyperparameters or sample sizes |
| Forcing all fields into a Methodology Matrix | Theoretical math has no "datasets and metrics." Adapt output to the field |
| Using citation velocity to find bleeding-edge papers | 6-18 month citation lag means velocity = 0 for actual breakthroughs |
| Inferring lab leadership from author position | Last-author = PI only in biomedicine. Alphabetical in econ/math. Ask, don't assume |
| Filtering preprints by "author prestige" or GitHub stars | Hardcodes the Matthew Effect, blinds agent to novel work from unknown researchers |
| Autonomous branch selection without user input | The agent is a research assistant, not an oracle. Always let the human steer |
| Relying on a single survey paper as the taxonomy | Inherits one author's biases and blind spots. Cross-reference or warn explicitly |
| Generating narrative prose instead of structured tables | Tables are scannable, auditable, and expose gaps. Prose hides them |
| Running serial API calls as LLM tool invocations | Slow and context-expensive. Batch all fetching into the Python script |

---

## Confidence Tagging System (3-Tier)

| Tag | Criteria | When to Use |
|-----|----------|-------------|
| `[FROM API]` | Data returned directly by Semantic Scholar or full-text fetch | Citation counts, author lists, venues, OA status, paper existence |
| `[SYNTHESIZED]` | LLM inference from multiple API-grounded data points | SOTA summaries, gap analysis, branch descriptions |
| `[METADATA ONLY]` | Paper exists in graph but full text was not accessible | Paywalled papers — methodology and limitations are UNKNOWN |

---

## Example Invocations

```
"literature review on graph neural networks for drug discovery"
→ Ask for seeds. Empirical → Methodology Matrix. bioRxiv-heavy = good OA coverage.

"what papers exist on zero-knowledge proof composition"
→ Theoretical/formal CS → Theorem Lineage. Proof technique evolution + open conjectures.

"prior research on algorithmic fairness in hiring"
→ Mixed empirical + qualitative. Ask user which lens. May need both templates.

"state of the art in protein folding since AlphaFold"
→ Survey-paper shortcut (many recent reviews). Warn about inherited bias.

"scholarly review of mechanism design in auctions"
→ Theoretical economics. Alphabetical authorship. Heavy paywall presence warning.
```

---

## Failure Modes & Graceful Degradation

- **S2 returns 0 results**: Verify title/DOI spelling. Fall back to WebSearch → extract S2 ID manually
- **Rate-limited (429)**: Script handles backoff. If persistent, reduce to references-only
- **All papers paywalled**: Report honestly, present metadata table, suggest different branch
- **No seed papers + broad topic**: Survey-paper hunt first, present top 5 as candidate seeds
- **NetworkX install fails**: Fall back to pure Python dict-of-dicts graph (no community detection)
- **Sparse graph (<10 papers)**: Expand to 2-degree neighborhood. If still sparse, report "nascent field"
- **User wants all branches**: Process sequentially, one per turn. Warn about context limits

---

## Token Budget

Total: ~25,000-40,000 tokens. Phase 4 (full-text extraction) is the main
cost at ~15,000-30,000 tokens. Use `/compact` between Phase 3 and Phase 4
if context is heavy. All graph computation happens in Python — only the
pruned summary enters LLM context.

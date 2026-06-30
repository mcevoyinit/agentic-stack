---
name: airplane
description: |
  Pack a flight. Distill the most important things you should LEARN and KNOW
  about a topic (or the current session's work) into one self-contained,
  offline-readable academic PDF, finished in a clean whitepaper style.
  Gathers everything online FIRST, embeds it (no dangling links), adds an
  active-recall study section, and exports to your learning output dir with a
  timestamp. Hands the final formatting + PDF build to /academic-format.
  Trigger: "/airplane", "airplane", "going on a flight", "offline reading",
  "pack me a flight", "plane reading on X", "study pack for the plane",
  "make me a whitepaper to learn X offline".
  DO NOT activate for: live research you can keep doing online (use /feynman
  or /deep-research), a session closeout (use /gtg or /wrap), or a normal PDF
  with no offline-learning intent (use /academic-format directly).
---

# /airplane — Offline Study Pack Builder

The user is about to lose internet (a flight, a dead zone, a focus block).
The job is to hand them ONE PDF that contains the most important things they
should learn and know about a topic, fully self-contained, so they can read
and actually study it with no connection. The visual finish is a clean
academic whitepaper look. The output is a learning artifact, not a summary
dump.

## What this skill is and is not

| Is | Is not |
|----|--------|
| Offline study pack | Live research session |
| Self-contained PDF | A page of links to read later |
| Active-recall learning doc | A flat executive summary |
| Whitepaper finish | A plain markdown export |

The defining constraint: **after this runs, the user has NO internet.**
Anything they need to learn the topic must already be inside the PDF.

## Input modes

Detect from the invocation. If ambiguous, ask one question, then proceed.

| Mode | Trigger | Source of content |
|------|---------|-------------------|
| **Topic** | `/airplane <topic>` | Research it NOW (online), then pack |
| **Session** | `/airplane this` / `/airplane session` | The current session's work + decisions |
| **Project** | `/airplane <project>` | Memory + KB + repo + conversations |
| **Docs** | `/airplane <file/dir>` | The named source material, distilled |

## Workflow

### Step 1. Scope it (one question max)

Confirm: the topic, the depth (primer / working knowledge / deep), and
roughly how long the flight is. Map flight length to target size:

| Flight | Target | Depth |
|--------|--------|-------|
| Short (< 2h) | 6–10 pages | Primer: the spine + the must-knows |
| Medium (2–5h) | 12–20 pages | Working knowledge + worked examples |
| Long (5h+) | 20–35 pages | Deep: derivations, edge cases, exercises |

If the user already named the topic and there is an obvious depth, skip the
question and state the assumption in one line.

### Step 2. Gather EVERYTHING online (you only get one shot)

This is the load-bearing step. Once the PDF is built the user is offline, so
be exhaustive now. Fan out:

- For **Topic** mode: WebSearch + WebFetch the canonical sources, primary
  papers, and the best explainers. Pull the actual content, not just titles.
  Consider spawning parallel Explore / research subagents per subtopic.
- For library/framework topics: use context7 (`resolve-library-id` then
  `query-docs`) so the embedded reference is current, not from memory.
- For **Session / Project**: pull from the conversation, memory files, KB
  (`get_topic`), and the repo. Embed the real code and real decisions.
- Capture diagrams as ASCII (they survive offline and need no image fetch).

Verify before embedding. Do not pack a false positive into something the
user will study as ground truth. Flag anything you could not verify as
"unverified" inside the doc rather than stating it flat.

### Step 3. Distill to "what to LEARN and KNOW"

Do not transcribe. Compress to the essential. Every section earns its place
by answering: *what does the user not yet know that they need to?*

Build the markdown with this spine (adapt section count to depth):

```
Title  +  one-line "why this matters to you"
Abstract            — what this pack teaches, in 4–6 lines
1. The 60-second model   — the whole topic in one mental picture
2. Core concepts         — defined, each with a why-it-matters line
3. How it actually works — mechanism, with ASCII diagrams
4. Worked examples       — concrete, end to end, no hand-waving
5. The sharp edges       — gotchas, failure modes, common wrong models
6. Where it connects     — how it ties to what the user already does
7. Active recall         — questions FIRST, answers in an appendix
8. One-page cheat sheet  — the dense reference card
References               — full citations, embedded (they can't click them)
Appendix A. Answer key   — answers to the §7 questions
```

The **Active recall** section is mandatory and is what makes this a study
pack rather than a summary. Write 8–20 questions that force retrieval (not
recognition). Put answers in the appendix so they can self-test on the
plane.

The **cheat sheet** is the dense one-pager they keep after the flight.

Personalize §6: tie the topic to the user's live context (their current
projects, work, or learning goals) so the learning has a hook. Read memory
if the connection is not obvious.

### Step 4. Hand off to /academic-format for the whitepaper finish

Write the distilled markdown to a temp file, then invoke **/academic-format**
to validate structure / cross-refs / citations and build the PDF. Tell it to
use a clean whitepaper finish via a header include if you have one:

```bash
pandoc <input>.md -o "$EDU_DIR/airplane-<slug>-<YYYYMMDD-HHMM>.pdf" \
  --pdf-engine=xelatex \
  -V geometry:margin=1in -V fontsize=11pt -V documentclass=article \
  --include-in-header="$EDU_DIR/whitepaper-style-header.tex" \
  --toc --number-sections
```

`$EDU_DIR` defaults to `~/education/`. If a custom header
(`$EDU_DIR/whitepaper-style-header.tex`) is missing, fall back to
/academic-format's default academic style and say so.

The `.tex`/intermediate file keeps a timestamp in its name for versioning.
The PDF lands in `$EDU_DIR` (never ~/Downloads).

### Step 5. Deliver

Run /academic-format's validation gate — no export until structure,
cross-refs, citations, and content checks pass. Then report:

```
AIRPLANE PACK READY

  Topic     <topic>            Depth: <primer|working|deep>
  Pages     N                  Sized for: <flight length>
  Verified  <sources checked>  Unverified flags: <n or none>

  PDF   $EDU_DIR/airplane-<slug>-<ts>.pdf

  Inside: <n> concepts · <n> worked examples · <n> recall questions
          + one-page cheat sheet + embedded references (offline-safe)
```

Give the full absolute path (the user pastes it). Offer to AirDrop / copy to
a device or to also drop a plain `.txt` of the cheat sheet if they want it
readable without a PDF viewer.

## Hard rules

1. **Offline-safe or it failed.** No "see this link", no figures that need a
   network fetch, no "look this up". If it is needed, it is embedded.
2. **Verify before you pack.** A study pack that teaches a wrong fact is
   worse than no pack. Flag the unverified, never launder it as fact.
3. **Learning artifact, not a summary.** The active-recall section and cheat
   sheet are mandatory. A flat summary is a failure of this skill.
4. **Whitepaper finish** via the style header. Fall back only if absent, and
   say so.
5. **Output to `$EDU_DIR` with a timestamp.** Never ~/Downloads.
6. **Full absolute paths** in the report.
7. **One gather pass, be exhaustive.** You do not get a second shot once the
   user is airborne. Over-gather in Step 2.

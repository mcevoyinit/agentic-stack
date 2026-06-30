---
name: learn
description: |
  Feynman-Method learning loop. Turns reading into remembering by forcing
  active recall: you write the explanation, not Claude. Four turns in one
  ~20-minute session — Concept Map (with a visual when the idea is
  structural), You First (you attempt + rate confidence before seeing any
  answer), the Gap Finder (honest report card + calibration on YOUR words),
  and the Analogy Lock. Saves a
  self-TEST card (questions, not answers) to your learning output dir so
  next-day review is retrieval, not re-reading. Grounded in retrieval
  practice (Karpicke & Blunt 2011), the generation effect (you attempt
  before seeing the answer), the protege effect (Koh 2018), desirable
  difficulty (Bjork 1994), dual coding (Paivio 1986), and confidence
  calibration (you rate certainty, then see if it was warranted).
  Trigger: "/learn", "learn this", "make this stick", "feynman method",
  "feynman this", "help me remember", "active recall on X",
  "I just read X and want it to stick", "run the 4 prompts".
  DO NOT activate for: deep multi-source research with citations (use
  /feynman), an offline study PDF for a flight (use /airplane), or a quick
  factual answer with no intent to retain (just answer).
---

# /learn — Feynman Active-Recall Loop

Most people forget ~80% of what they read within a month (the Ebbinghaus
forgetting curve). The fix is not more reading — it is retrieval. This skill
runs the 4-step Feynman Method as a guided loop so a topic actually sticks.

The defining mechanic: **the user writes the explanation, not Claude.**
Reading the model answer is recognition. Typing their own version is
retrieval. Only retrieval builds memory. If the loop ever generates the
user's answer for them, the skill has failed — it has produced the exact
fluency illusion it exists to break.

## The load-bearing rule (read twice)

The user attempts the explanation FIRST, before they see any model answer
from you. This is the generation effect: a cold attempt, even a wrong one,
builds memory; reading your answer first turns it into recognition (the
trap). So at Prompt 2 you ask for THEIR version and **STOP and wait** — you
do NOT show your model answer, do NOT write their version, do NOT paraphrase
what they "would say". Your model answer is revealed only at Prompt 3, next
to theirs, as the comparison. End the Prompt 2 turn with the ask and nothing
after it.

Stuck-not-lazy exception: if the user genuinely has no idea where to start,
give ONE small hint or the first sentence of a worked example, then ask them
to continue from there. A total novice needs a toehold (worked-example
effect). That is different from handing them the whole answer.

If the user tries to skip the typing ("just do it for me", "give me all
four"), say once, plainly: the attempt IS the learning; without it this is
just a fancy summary and they'll forget it. Then let them decide. If they
still want the passive version, give it but label it "summary, not
retrieval".

## Inputs

Detect the topic and the source from the invocation:

| Source given | What to do |
|--------------|------------|
| A file/PDF/article path | Read it; that is the source of truth |
| Pasted text | Use the pasted text as the source |
| Just a topic name | Use your own knowledge; web-check only if the topic is fast-moving or you're unsure |
| Nothing | Ask one line: "What do you want to make stick?" |

Stay grounded in the source when there is one. Do not import outside facts
that contradict it without flagging them.

Light scope check (one line, only if it matters): if the topic is big or the
user's level is unclear, ask ONE question before starting — "what's the goal:
remember it, explain it to someone, or apply it?" Don't present a menu of
modes; one question, then go.

## Failure modes to handle

| Failure | What to do |
|---------|------------|
| Lazy 2-word answer | Don't grade it. Push back once, ask for a real attempt |
| "Just do it for me" | Say the attempt is the learning; offer summary-only if they insist, labelled as such |
| Genuinely stuck novice | Give one hint / first line, let them continue (worked example) |
| Topic too big for one loop | Split it. Do the top 5 ideas now, name the rest, offer a second session. Don't cram 15 ideas |
| You're unsure of a fact | Verify or mark "(uncertain)". Never drill a guess into them |
| They ace everything first try | Topic may be too easy or your bar too low. Push to apply/contrast/boundary questions, not just "explain" |

## Accuracy guard (you are the source — don't be wrong)

When teaching from your own knowledge, a confident wrong explanation is
worse than no skill at all: the user will lock in the error with full
retrieval. So:
- If the topic is fast-moving (a protocol, a product, current events, a
  library version, anything that changes) OR you are not certain, verify
  the 5 ideas with a quick web/source check BEFORE Prompt 1. Don't teach
  stale facts as gospel.
- If a fact is genuinely uncertain after checking, mark it "(uncertain)"
  rather than asserting it. Never let the user memorise a guess as a fact.
- When there is a source (file/paste), it wins over your memory; flag any
  conflict instead of silently overriding.

## Output style

- Terse. Each line ≤ 72 chars. Short sentences, not paragraphs.
- 12-year-old register means PLAIN, not childish. No jargon, no hedging.
- No hyphens or em-dashes in prose (commas/periods instead).
- Tables for the concept map and report card, not bullet walls.

## Visuals — dual coding (use when the concept is structural)

A picture stored alongside words is retained far better (Paivio). But a
forced diagram on an abstract idea is noise. So gate it:

| Draw a visual when the idea is... | Skip it when the idea is... |
|-----------------------------------|------------------------------|
| Structural (parts + how they wire)| A plain definition |
| A flow / sequence / pipeline      | A single principle or value |
| A hierarchy or tree               | A vibe or judgement call |
| A timeline                        | Something purely verbal |
| A tradeoff / before-vs-after      | |

Medium, in order of preference:
1. **ASCII diagram inline** — always visible in the terminal, zero deps.
   Default to this.
2. **Rendered image** — only if the user wants it or the structure is too
   rich for ASCII. Render to `$LEARN_OUTPUT_DIR/<slug>-<n>.png` via whatever
   is on the box (mermaid `mmdc`, graphviz `dot`, or a tiny matplotlib
   script), then open it. If none are available, fall back to ASCII, don't
   block.

The strongest move (retrieval + dual coding): at the Lock turn, ask the user
to SKETCH the structure from memory first (on paper, or describe it in
words), THEN show the model diagram so they can compare. Drawing from memory
is itself retrieval. Offer this for structural topics; don't force it.

## The loop

Run these in order. One prompt per turn. Never bundle them.

### Prompt 1 — Concept Map (1 turn)

Find the load-bearing ideas. Most topics have 50 facts; a handful carry the
weight. Use 5 as the default, but flex to the topic: 3 for a small idea, up
to 7 for a big one. Don't pad to hit a number.

For each idea give exactly:
- Definition: one plain sentence.
- Why it matters: one line, real-world.
- The test question: the one question that proves you get it.

Format as a table (Idea / Plain definition / Why / Test-Q).
If the topic as a whole is structural, add ONE ASCII overview diagram under
the table showing how the ideas connect (see Visuals). Skip if abstract.
Close with: "Pick which to explain first, or say 'all'."

### Prompt 2 — You First (THE PAUSE)

Do NOT give your explanation here. Ask the user to explain the ideas
themselves, cold. For each idea they should give:
- Their plain-English explanation (teach it to a 12-year-old).
- One example of their own (not one you handed them).
- A confidence rating 0-10: how sure are they they're right?

Batch vs one-at-a-time: for an easy or small topic, let them do all the
ideas in one go. For a hard or unfamiliar one, do ONE idea at a time
(attempt → reveal+grade → next). One-at-a-time gives feedback at the moment
of encoding; a batch-of-five then a feedback dump is weaker. Offer the
choice if unsure.

Then STOP. End the turn with:
"Your turn first. Explain each in your own words, give your own example, and
rate your confidence 0-10. Don't worry about being wrong, the attempt is the
point. I'll show mine after. Send when ready."

Do not proceed. Do not show your model answer. Wait for their message. (If
they are genuinely stuck, use the stuck-not-lazy exception above.)

### Prompt 3 — The Gap Finder (after the user sends their attempt)

NOW reveal your model answer for each idea, placed next to theirs, so they
see the gap themselves. Then grade. Quote their actual words before
critiquing them (no critiquing a paraphrase). Lazy-answer guard: if an
answer is two words or dodges the mechanism, don't grade it, push back once
and ask them to actually attempt it.

Grade each against a real rubric so STRONG means something:
- STRONG: names the mechanism (the causal "why", not just the "what") AND
  would survive their own test-question.
- WEAK: right direction, but vague, missing the mechanism, or hand-wavy on
  the part that matters.
- WRONG: a real misconception, a reversal, or a confident error.
Default to WEAK when unsure. Grade hard; an undeserved STRONG locks in a gap.

Add a calibration read per idea, comparing their confidence to their grade:
- High confidence + WEAK/WRONG = "overconfident" (the dangerous case, flag
  it loudest — this is the fluency illusion caught in the act).
- Low confidence + STRONG = "underconfident, you knew it".
- Matched = "well calibrated".

For each idea:
1. Grade + calibration.
2. If WEAK/WRONG: name exactly what they confused. Specific, not polite.
3. Corrected version in plain words, using a DIFFERENT analogy than the source.
4. One follow-up, varied by what they need (not always "explain again"):
   apply it to a new case, contrast it with a near neighbour, or name where
   it stops being true (boundary). These beat re-explaining (elaborative
   interrogation + contrasting cases).

Format as a table (Idea / Grade / Calibration / What broke), corrections
below. End: "Restudy THIS first: <the single highest-leverage gap>."

This is the step a book can never give — it can't see where THEIR logic
broke.

### Prompt 4 — The Analogy Lock (final turn)

For each idea, two analogies:
- From everyday life (cooking, driving, sport, weather, money).
- From adult experience (a job, a phone, time, money).

For each analogy: where it works, AND where it breaks (mandatory — every
analogy breaks somewhere; naming the limit stops a wrong mental model).

For structural ideas, this is the place to offer the sketch-from-memory move
(see Visuals): ask the user to draw/describe the structure, then show the
model diagram to compare. Optional, don't force it.

End with a one-line summary per idea (the "what they should be able to
say"), shown in chat. Then SAVE the self-test card (next section) — note the
SAVED file holds the QUESTIONS, not these answers.

## Save a self-TEST card (after Prompt 4) — the anti-re-read fix

Re-reading answers feels productive and teaches nothing (the fluency
illusion this skill exists to break). So the saved artifact is a TEST, not a
summary. Tomorrow the user retrieves first, then checks themselves.

Path: `$LEARN_OUTPUT_DIR/learn-<topic-slug>-<YYYY-MM-DD>.txt`

`$LEARN_OUTPUT_DIR` defaults to `~/education/`. Set it in your shell env to
point somewhere else if you prefer.

File body (no header lines that bleed on paste):
```
<topic> — self-test, learned <date>

Cover the answers. Say each answer out loud before you look.

Q1. <question for idea 1>
Q2. <question for idea 2>
Q3. <question for idea 3>
...

(Mix the question types, don't make them all "explain X": at least one
"apply it to <new case>", one "how is it different from <neighbour>", and
one "when does it stop being true". Varied retrieval beats rote recall.)

--- answers (only after you've tried) ---
A1. <one-line summary for idea 1>
A2. <one-line summary for idea 2>
A3. <one-line summary for idea 3>
...
```
Give the user the full absolute path. Tell them: tomorrow, answer the
questions from memory BEFORE scrolling to the answers. That retrieval is the
point; re-reading the answers is not.

## Spaced repetition (offer, don't impose)

The curve says re-test at expanding intervals. After saving, offer ONE line:
"Want me to set a re-test? I can ping these questions back to you tomorrow,
in 3 days, and in a week." If yes, wire it via /schedule (or a todo list for
a single next-day nudge). Send the QUESTIONS, never the answers. Don't
auto-create anything.

## Naming note

The `/feynman` skill is a research harness, NOT this learning loop.
This is `/learn`. Don't conflate them.

## What good looks like

- The user typed their own explanations at least once. (Non-negotiable.)
- The report card named at least one gap they didn't know they had.
- Facts taught were verified, not confidently guessed.
- Structural ideas got a visual; abstract ones didn't get forced one.
- They walk away with a self-TEST card on disk (questions, not answers).
- Total time ~20 min, four turns of real retrieval.

---
name: red-team
description: >-
  CIA Tradecraft Primer method for stress-testing a decision before you
  commit to it. Runs 4 sequential adversarial passes — Key Assumptions
  Check, Pre-Mortem, Hostile Competitor, 1-Star Review — each as a fresh,
  unrapport'd subagent so it attacks without the social softening a long
  conversation builds up. Ends with a GO / KILL verdict and the specific
  fixes needed to survive.
  Trigger: "/red-team", "red team this", "red team my idea", "kill my
  idea", "run the 4 prompts", "CIA red team", "pre-mortem this",
  "stress-test this decision", "devil's advocate this".
  DO NOT activate for: routine code review (use /code-review), a quick
  pros/cons list the user didn't ask to be adversarial about, or a decision
  that's already irreversible and executed (this is a pre-commitment tool).
---

# Red Team — CIA Tradecraft Primer, 4-prompt method

Source: CIA's declassified Tradecraft Primer (2009) — Key Assumptions
Check, Devil's Advocacy / Red Team Analysis — plus Gary Klein's
Pre-Mortem (HBR 2007) and a demand-side customer critique. Reference:
`cia.gov` Tradecraft Primer; Foreign Policy's 2015 Red Cell piece.

## Why fresh subagents, not you

Sycophancy is the failure mode this whole method exists to defeat. If
you (the agent holding this conversation) write all four passes
yourself, you're grading your own rapport with the user — you already
know they're invested in the idea, and that softens the output even
when you try not to let it. Each pass below must run as an
**independent Agent call with only the idea description**, no
conversation history, no knowledge of how much the user wants this to
work. That's what makes it actually adversarial instead of performed.

## Step 0 — Establish the target

If the idea/decision isn't already crystal clear from context, ask
the user directly: what is it, who is it for, what does success look
like, what's the timeframe. One paragraph is enough. Do not proceed on
a vague target — vague targets produce vague red-team output (per the
source material: "specific enemies produce specific plays").

If the decision has context in notes, memory files, or project docs
you keep, read the relevant file(s) first and fold the real facts into
the one-paragraph brief you hand each subagent — the subagents get the
*facts*, not the emotional investment.

## Step 1 — Run the 4 passes, in order, each a fresh Agent call

Run these **sequentially**, not in parallel — each one is a distinct
lens and the source material specifies this exact order (assumptions
first, then failure simulation, then competitive attack, then
emotional-honesty check). Use `subagent_type: general-purpose` for
each. Give each subagent ONLY the idea brief — never paste this
skill's framing, never mention the user's emotional stake, never
soften the ask.

**Pass 1 — Key Assumptions Check**
```
You are a CIA Red Team analyst. Do not evaluate whether this idea is
good. Your only job is to audit the assumptions it depends on.

IDEA: <brief>

1. List every assumption this plan depends on, including hidden ones
   not stated outright. At least 10.
2. Classify each: LOAD-BEARING (if wrong, the plan fails) / IMPORTANT
   (weakened but survives) / MINOR.
3. For each LOAD-BEARING assumption: what specific evidence would
   prove it wrong? If none exists, say so explicitly.
```

**Pass 2 — Pre-Mortem**
```
It is 18 months from today. This idea has failed catastrophically —
not "did okay," failed, burned, embarrassing.

IDEA: <brief>

Write the honest post-mortem, chronological:
- Months 1-3: early warning signs ignored
- Months 4-9: decisions that made it worse
- Months 10-15: point of no return
- Months 16-18: the collapse and its cost
Be specific, name exact mistakes. End with: "The root cause was ___."
```

**Pass 3 — Hostile Competitor**
```
You are a competitor with $100M funding, world-class talent, personal
motivation to crush this idea. 90 days, unlimited budget.

IDEA: <brief>

Write a 90-day attack plan:
- Days 1-30: study, copy, reposition
- Days 31-60: launch a better version
- Days 61-90: starve the original of customers/attention/talent
- What is the original uniquely vulnerable to that it doesn't see?
End with: "The weakness that lets me win is ___."
```

**Pass 4 — 1-Star Review**
```
You are a customer who tried this and hated it — spent real money,
real time, feels cheated.

IDEA: <brief>

Write the 1-star review that goes viral: specific, funny, brutal, in
the angry-but-articulate voice. Then 3 follow-up tweets quoting it
with their own complaints.
End with: "The single thing that made me feel cheated was ___."
```

## Step 2 — Synthesize (this is your job, not a subagent's)

Pull the four punchline lines together:
- The load-bearing assumptions with no evidence
- The root cause
- The weakness that lets the competitor win
- What made the customer feel cheated

Look for a pattern across all four. If 3+ independently point at the
same underlying flaw, that's signal, not coincidence.

Render one verdict:

- **KILL** — load-bearing assumptions unverifiable AND root cause
  unfixable. Say so plainly. This is the good outcome, not a failure
  of the exercise — cheaper to kill it here than after 6 months.
- **FIX AND PROCEED** — criticisms are real but addressable. Name the
  2-3 specific fixes required before proceeding, tied directly to
  what the passes surfaced (not generic advice).

## Step 3 — Save the report

Write the full four-pass output + synthesis + verdict to a plain-text
file — this is a document for the user to read, not a skill/memory
artifact. Default location
`$RED_TEAM_OUT_DIR/<idea-slug>-<YYYYMMDD-HHMM>.txt` (default
`~/red-team/`, <CUSTOMISE> to taste) unless a specific project
directory is obviously in play — ask if unclear. Give the user the
full absolute path.

Do not paraphrase the subagent output when writing the file — include
the actual four passes in full so the user can see the raw adversarial
reasoning, not just your summary of it.

## What NOT to do

- Don't run the passes yourself inline — that defeats the anti-
  sycophancy purpose of fresh, uninvested subagents.
- Don't soften a KILL verdict into "worth reconsidering." If the
  method says kill it, say kill it.
- Don't skip a pass because the idea "obviously" survives it — the
  whole point is that instinct is exactly what this checks.
- Don't run this against something already executed and irreversible
  — it's a pre-commitment tool, not a retrospective (use `/forensic`
  or a plain post-mortem for that).

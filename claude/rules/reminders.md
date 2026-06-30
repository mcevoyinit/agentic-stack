# Reminders Protocol

Single source of truth for your live todo list: `$TODO_FILE`
(default `~/todo.md` — set the env var to relocate it).

## When to append to the todo file

Trigger phrases from the user:
- "remind me to X"
- "remind me about X"
- "put X on my list" / "add X to my todo"
- "I need to X tomorrow / on [day]"
- "don't let me forget X"

When triggered, append `- [ ] X` under the correct date heading in
`$TODO_FILE`.

If a date is specified (e.g. "tomorrow", "Friday", "May 3"), resolve
it to an absolute date and put the item under a `## [Day Date Month
Year]` heading, creating the heading if it doesn't exist.

If no date is specified, add to the `## Open (no date)` section.

Confirm in one short line. Don't over-explain.

## When to check the todo file

- Start of a daily-briefing skill, if you build one — pull items
  from today's date and the `Open (no date)` section
- If the user asks "what's on my list" / "what do I need to do" —
  print the file
- If the user says "done with X" / "clear X" / "tick off X" — mark
  the matching line as `- [x]` rather than deleting

## Hygiene

- Items checked off (`- [x]`) older than 7 days can be pruned during
  a periodic review (prune silently unless the item was high-stakes
  — then confirm first)
- Past date sections with all items checked off can be collapsed or
  deleted after the date passes
- Never delete an unchecked item without confirmation

## Congruency with other protocols

- Any daily-briefing skill should read this file — don't maintain a
  separate pending-actions list elsewhere
- Long-term memory is for durable context, not day-to-day todos —
  don't cross-contaminate
- Calendar events from your calendar provider stay in calendar;
  todos are for action items without a fixed meeting

<!-- CUSTOMISE: set $TODO_FILE in your shell profile or
     CLAUDE.md, e.g. export TODO_FILE=~/todo.md -->

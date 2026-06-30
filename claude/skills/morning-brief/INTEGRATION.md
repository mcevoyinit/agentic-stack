# morning-brief — integration & setup guide

This is the flagship skill in this bundle: a daily briefing agent that
reconciles a todo list against ground truth, classifies your contacts by
who-owes-whom-a-reply, and renders a two-message glance-card + detail
report. The architecture is real and battle-tested; the personal data
(names, figures, file paths, account-specific senders) has been stripped
from `SKILL.md`. This guide is what you need to stand it up yourself.

## 1. What you need before this works at all

| Need | Why | Where |
|------|-----|-------|
| An email MCP server | Section 2 (inbox triage), Section 0.1 (ground truth) | Gmail/Outlook MCP, or write your own |
| A calendar MCP server | Section 1 (schedule) | Google Calendar MCP, or your provider's |
| A chat MCP server | Section 2b (chat triage) — optional | WhatsApp/Slack/Telegram MCP, or skip this section |
| `$TODO_FILE` | Section 5 (pending actions) | A flat markdown file, see `claude/rules/reminders.md` |
| `$BRIEF_VERIFIER_DIR` | Section 0 (verifier preflight) | You build this — see §3 below |

If you only wire up email + calendar, you already get a useful brief:
Sections 1, 2, 4, 5 work with nothing else. Sections 0.4, 2b, 2c, 2d, 2e,
3, 3b, 5b are all optional layers you add incrementally.

## 2. Minimal path (1-2 hours)

1. Get an email MCP and calendar MCP connected (check your Claude Code
   MCP marketplace, or `claude mcp add` a community server).
2. Create `$TODO_FILE` (e.g. `~/todo.md`) with the structure from
   `claude/rules/reminders.md` (`## Open (no date)` heading required).
3. Set `$BRIEF_TZ` and `$BRIEF_CITY` in your shell profile.
4. Run `/morning-brief`. Sections 0/0.4/2b/2c/2d/2e/3/3b/5b will report
   "offline" or get skipped gracefully — that's expected and fine.
5. Iterate from there.

## 3. Building the verifier (Section 0)

The verifier is the single highest-leverage piece of this skill — it's
what stops a daily brief from nagging you about things you already did.
It does NOT ship here because it's inherently tied to your own todo
format and your own ground-truth sources. Build it as a small Python
project with this shape:

```
$BRIEF_VERIFIER_DIR/
  verify.py            # rule engine: claim type -> evidence check
  orchestrate.sh        # runs verify.py, writes proposals.md
  claims.py             # extracts named-counterparty claims (Section 0.4)
  fanout.py             # builds subagent prompts from claims
  merge_verdicts.py     # merges subagent JSON verdicts
  proposals.md           # OUTPUT: today's reconciliation (generated)
  verified-closures.md   # OUTPUT: audit log, append-only (generated)
```

**`verify.py` rule shape** (one rule per obligation type you care about):

```python
def check_reply_sent(todo_item, gmail_sent_dump, chat_outbound_state):
    """Return ('closed'|'open', evidence_str) for a 'reply to X' todo item."""
    counterparty = extract_counterparty(todo_item.text)
    for thread in gmail_sent_dump["threads"]:
        if counterparty_in_thread(counterparty, thread):
            return "closed", f"sent mail in thread {thread['id']}"
    if chat_outbound_state.has_recent_outbound(counterparty):
        return "closed", "outbound chat message found"
    return "open", None
```

Start with 2-3 rules (reply-sent, payment-confirmed, file-exists) and add
more as you notice the brief re-surfacing things you've done.

**`orchestrate.sh` shape:**

```bash
#!/bin/bash
set -euo pipefail
python3 "$(dirname "$0")/verify.py" \
  --todo "$TODO_FILE" \
  --gmail-sent /tmp/gt-mail-sent.json \
  --gmail-pay /tmp/gt-mail-pay.json \
  --out "$(dirname "$0")/proposals.md" \
  "$@"   # pass through --apply if given
```

Run it read-only for at least two weeks before trusting `--apply` to
auto-tick your todo file.

## 4. Building the chat classifier (Section 2b)

Same idea, smaller scope. A script that takes a JSON dump of recent chat
threads and classifies each into `awaiting_you` / `awaiting_them` /
`conversational` / `noise`, using deterministic rules (last-message
direction is the strongest single signal; question marks and explicit
asks are next). Don't reach for an LLM call here unless the deterministic
rules genuinely aren't enough — it's both faster and more debuggable as
plain Python.

## 5. Wiring the contact-state classifier (Section 2c)

This is pure logic, no external service: merge the outputs of Sections 1
(calendar attendees), 2 (email senders), and 2b (chat senders) into one
per-person state with a `last_contact_at` and `direction` field, then
bucket by your own thresholds (e.g. >7 days silent = `cold`).

## 6. Tracked metrics (Section 3) and the "never hardcode a number" rule

If you want a price tracker, a deadline countdown, or any other
recompute-every-day figure: read it from a file you maintain, not from
this skill's prompt text. See `infra-templates/canonical/` in this bundle
— it's a small SQLite-backed registry built exactly for this problem
(stale hardcoded numbers in prompts silently lying to you). The pattern:

```
canonical set --concept my-deadline --file ~/my-tracker.md --value "hint"
```

then in the skill: `canonical get --concept my-deadline` and trust the
file it points to, not a number baked into `SKILL.md`.

## 7. Cross-session state (Section 5b)

Optional, needs `infra-templates/recall-db` set up (see that directory's
README) plus your own indexer populating it from your Claude Code
transcripts. Until you build that, this section just doesn't render —
the skill handles its absence gracefully.

## 8. Tuning the output format

The two-message glance-card + detail pattern is the most "opinionated"
part of this skill. It was shaped by one real failure mode: a daily brief
that repeats the same name/task three times across different sections
stops getting read carefully. The fix — each fact gets exactly one
canonical home (the card OR the detail, never both in full) — is worth
keeping even if you change everything else.

If you don't like the emoji-landmark format, change it — just keep the
"once per fact" discipline, and keep the card to <72-char lines so it
doesn't wrap badly in narrow terminals or mobile notification previews.

## 9. Known sharp edges (carried over from production use)

- **MCP tools only work in the main conversation**, not in subagents —
  if you try to delegate Section 1/2/2b to a subagent, it silently can't
  reach your MCP servers. Run all MCP-touching sections in the main loop;
  only the Section 0.4 claim-verification fanout (which explicitly
  inherits MCP access) is safe to delegate.
- **Truncated thread summaries are a recurring false-positive source.**
  Any verifier rule that only looks at a search result's preview (not the
  full thread) will eventually mark something "still open" that's
  actually closed, because the closing message was buried below the
  truncation point. Always deep-read referenced threads before trusting
  a "still open" verdict (Section 0.1a).
- **A classifier that only looks at the last message preview** (not the
  full thread, not message direction) will misclassify who owes whom a
  reply as soon as a conversation gets a few messages deep. Build the
  classifier against full thread bodies from day one.

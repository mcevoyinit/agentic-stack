---
name: morning-brief
description: |
  Daily contextual briefing combining calendar, priority emails, chat
  threads, a contact-state classifier, tracked metrics (price/deadline/
  whatever you configure), weather, pending actions, and cross-session
  working memory into one concise morning report. Uses Gmail-equivalent,
  Calendar-equivalent, chat MCP, and a recall-db query layer. Can run
  on-demand or scheduled.
  Trigger: "morning brief", "morning briefing", "daily brief", "good morning",
  "start my day", "what's my day look like", "/morning-brief".
  DO NOT activate for: general email questions (use a dedicated email-digest
  skill), calendar-only questions (just call the calendar MCP directly), or
  weather-only questions.
version: 1.0.0
---

# Morning Brief — Daily Contextual Briefing

> See your whole day in one glance before opening any app.
> Calendar + email red flags + your tracked metrics + weather + pending actions.

**Before using this skill, read `INTEGRATION.md` in this same directory.**
It is the setup guide: which MCP servers you need, which files you must
create, and every place marked `<CUSTOMISE>` below that you need to fill
in with your own data sources. This skill ships as architecture + working
mechanism, not a finished personal briefing — there is no way to ship a
working brief without your calendar, your inbox, your contacts.

## Activation

```
ACTIVATE when user says:
  "morning brief", "morning briefing", "daily brief", "good morning",
  "start my day", "what's my day look like", "brief me", "/morning-brief"

DO NOT activate for:
  - "check my emails" → use a dedicated email-digest skill
  - "what's on my calendar" → just call the calendar MCP directly
  - "what's the weather" → just WebSearch
```

## Execution Protocol

Run ALL sections in parallel where possible. The brief should take < 30 seconds.

### Section 0: VERIFIER PREFLIGHT (MANDATORY — runs BEFORE every other section)

**The core idea worth stealing from this skill, even if you build nothing
else here:** a daily brief that re-reads a flat todo file every morning
will keep surfacing items you already closed — emails you already sent,
bills you already paid, files you already shipped. Trust erodes fast once
that happens a few times. The fix is a verifier step that reconciles your
todo list against ground-truth signals BEFORE the brief renders anything.

A verifier at `$BRIEF_VERIFIER_DIR` (default `~/.morning-brief/verifier/`,
<CUSTOMISE>) reconciles `$TODO_FILE` against ground-truth signals (sent-mail
search, payment-confirmation search, outbound-chat search, filesystem
mtimes). This script is NOT included — `verify.py` / `orchestrate.sh` /
`claims.py` / `fanout.py` / `merge_verdicts.py` referenced below are your
own build. What ships here is the PATTERN; see INTEGRATION.md for a
from-scratch implementation outline.

**Step 0.1 — fetch ground-truth dumps in PARALLEL.** Two searches against
your email provider; a chat-outbound source is optional and skipped if
your chat MCP cannot stream outbound yet.

```
SENT_SINCE = today - 14 days       # provider's date-query format
PAY_SINCE  = today - 30 days

<email_mcp>.search_threads(
    query=f"in:sent after:{SENT_SINCE}",
    pageSize=50)
Write("/tmp/gt-mail-sent.json", json.dumps(response))

<email_mcp>.search_threads(
    query=f"({your_payment_sender_allowlist}) after:{PAY_SINCE}",
    pageSize=50)
Write("/tmp/gt-mail-pay.json", json.dumps(response))
```

<CUSTOMISE>: `your_payment_sender_allowlist` is a list of `from:` domains
for the banks/processors/payment providers you actually use — replace
with your own (e.g. your bank, your card processor, your travel booking
sites).

If either fetch errors, continue but note the gap; the verifier should
accept missing adapters gracefully (fewer closures, no false positives).

**Step 0.1a — deep-read referenced threads (MANDATORY).** `search_threads`
returns thread summaries with TRUNCATED message lists. For long active
threads, today's SENT messages can be buried below the truncation, which
causes the verifier to falsely flag a closed todo as still pending.

Before running the verifier, scan `$TODO_FILE` for unchecked lines that
mention an email thread id (regex `\b[0-9a-f]{14,20}\b` inside backticks).
For each such id, fetch the full thread and merge its SENT messages into
the sent dump before the verifier runs. This guarantees the verifier sees
every today's SENT message against an open todo, not just the top-N from
the bulk search.

**Step 0.1b — chat outbound** is fed by your own chat classifier (see
INTEGRATION.md), which writes a small state file your verifier reads as
its chat-outbound source.

**Step 0.2 — run the verifier.** Read-only by default:

```bash
bash $BRIEF_VERIFIER_DIR/orchestrate.sh
```

This writes `$BRIEF_VERIFIER_DIR/proposals.md` with three buckets:

  1. **Proposed [x]** — closed by ground truth (rule + evidence cited).
  2. **Needs human review** — referenced file missing, deadline passed, etc.
  3. **Still pending** — no ground-truth match yet; surface as work to do.

**Step 0.3 — propagate verifier output to downstream sections.** Read
`proposals.md` once. Section 5 (Pending Actions) MUST source from the
"Still pending" bucket only. Section 5 MUST NOT iterate raw `$TODO_FILE`
unchecked lines when proposals.md is available.

**Auto-apply policy.** Default is read-only (proposals only). Run with
`--apply` to mutate `$TODO_FILE` (`[ ] → [x]` with verified evidence) ONLY
when the brief is being run interactively and you've signalled trust.
Run any new verifier read-only for at least two weeks of soak before
trusting `--apply`.

**Failure mode.** If the verifier script is missing or exits non-zero,
emit one line at the top of the brief: `⚠ verifier offline — using raw
todo file (expect stale entries)`, then fall back to the prior behaviour.

### Section 0.4: CLAIM VERIFICATION FANOUT (shadow mode)

**Why this exists.** The rules-based verifier in Section 0 only sees claims
that have a matching rule plus a parsable signal. Composite claims that
originate from brain headlines, project memory cross-references, or a
contact-state classifier have no rule and no entry in `$TODO_FILE`, so they
slip through and get re-surfaced as pending even after the underlying
obligation has been closed elsewhere.

This section adds a second verification pass that does NOT rely on rules.
It extracts every claim with a named counterparty (from `$TODO_FILE`,
`proposals.md`, and your recall-db's open-threads query), fans out one
read-only subagent per claim, and each subagent verifies the claim against
ground truth via MCP tools.

**Shadow mode.** Until the false-positive rate has been measured against a
week of real briefs, this section is **purely additive**. It writes
verdicts to a log file and surfaces a one-line summary at the top of
Section 5. It does NOT yet drop `closed` claims from Pending Actions and it
does NOT mutate `$TODO_FILE`. Section 5 still renders from `proposals.md` as
before. The whole pipeline can be removed by reverting this section without
touching anything else.

**Step 0.4.1 — extract claims.**

```bash
python3 $BRIEF_VERIFIER_DIR/claims.py \
    --todo $TODO_FILE \
    --proposals $BRIEF_VERIFIER_DIR/proposals.md \
    --recall-db \
    --cap 15 \
    --out /tmp/brief-claims.json
```

This writes a JSON list of up to 15 claim records, each tagged with the
counterparty handle, obligation type (`payment` | `reply` | `document` |
`booking` | `dispute_chase` | `delivery`), source, and the time window to
search. Claims without a counterparty or recognized obligation are filtered
out — they belong in the regular Pending Actions list, not in the fanout.

**Step 0.4.2 — build subagent prompts.**

```bash
python3 $BRIEF_VERIFIER_DIR/fanout.py \
    --claims /tmp/brief-claims.json \
    --cap 15 \
    --out /tmp/brief-claim-prompts.json
```

Each prompt embeds the evidence checks for that claim's obligation type.
The subagent receives one claim, a list of MCP queries to run, and a
strict JSON output contract.

**Step 0.4.3 — fan out, one Agent call per claim, in a single message.**

Read `/tmp/brief-claim-prompts.json` and dispatch ALL prompts in a single
assistant turn using the `Agent` tool, one `Agent` call per claim. They
run in parallel. Subagent type: `general-purpose`. Each subagent inherits
MCP access from the main session — that is the whole point, the verifier
must see the same email and chat signals you see.

Each subagent MUST return exactly one JSON object matching this shape, no
prose:

```json
{
  "claim_id": "abc123",
  "verdict": "closed" | "open" | "ambiguous",
  "confidence": "high" | "medium" | "low",
  "evidence": "single sentence quoting the message id or tx hash that proves it",
  "evidence_refs": ["19e464b7b3f01774", "..."]
}
```

Collect every subagent's JSON object into a single file, then merge:

```bash
python3 $BRIEF_VERIFIER_DIR/merge_verdicts.py \
    --verdicts /tmp/brief-claim-verdicts.json \
    --claims /tmp/brief-claims.json \
    --summary-out /tmp/brief-verdict-summary.json
```

This appends today's closed and ambiguous verdicts to
`$BRIEF_VERIFIER_DIR/verified-closures.md` (audit log, append-only, never
mutates `$TODO_FILE`) and writes a structured summary that Section 5 reads.

**Step 0.4.5 — render in Section 5 (shadow).** Section 5's "Verified done
since last brief" subsection is augmented with this section's closures —
see Section 5 below.

**Failure mode.** If any of the three temp files is missing, render one
line at the top of Section 5: `⚠ claim verification offline — using
rules-based verifier only`, then fall back to the prior behaviour.

**Constraints, do not violate.**
- Cap fanout at 15 subagents per brief. If more verifiable claims exist,
  rank by `source_age_hours` descending and verify the top 15.
- Subagents are read-only. The prompt forbids sending any message.
- Evidence must be quotable: a specific message id, thread id, or
  transaction reference. Paraphrased evidence → `ambiguous`.
- Shadow mode for at least a week. Only switch to live mode (drop `closed`
  items from Pending Actions and auto-tick the todo file) once the
  false-positive rate is below 2% over the soak window.

### Section 1: TODAY'S SCHEDULE

**Time-awareness preamble (MANDATORY).** Before formatting the schedule,
capture `NOW = bash: TZ=$BRIEF_TZ date +%H:%M` (<CUSTOMISE> your timezone,
e.g. `America/New_York`). Split today's events into PAST (`end < NOW`) and
UPCOMING (`start >= NOW` or in-progress). Mark past events `[done]`,
in-progress `[now]`, and upcoming with no marker. State the brief's clock
at the top of Section 1.

Calendar attendees from PAST events feed the Contact State classifier
(Section 2c) as `Last: today HH:MM, State: met today` — not `scheduled`.
Marking a past event as "scheduled" is a real failure mode worth guarding
against explicitly.

```
Call: <calendar_mcp>.list_events
  timeMin: today 00:00:00
  timeMax: today 23:59:59
  timeZone: $BRIEF_TZ
```

Also peek at tomorrow with the same call shifted one day.

Format as a timeline:
```
09:00  Dentist appointment
11:30  Call with a colleague
14:00  Free
16:00  Driving theory session
```

Flag conflicts (overlapping events). Note gaps > 2 hours as "free blocks."

### Section 2: EMAIL RED FLAGS (Last 18 hours)

Triage fast — only surface RED FLAGS and items that need action TODAY.

```
Call: <email_mcp>.search_messages
  q: "after:{yesterday} -category:promotions {your_noise_sender_excludes}"
  maxResults: 30
```

<CUSTOMISE>: `your_noise_sender_excludes` is your own newsletter/
notification denylist (delivery apps, newsletters, automated digests).

Scan snippets only. Only deep-read messages that look:
- Urgent (bounced payment, security alert, deadline)
- From important contacts — <CUSTOMISE> your own VIP list, kept in a
  config file (e.g. `$BRIEF_VERIFIER_DIR/vip-senders.txt`), NOT hardcoded
  in this skill file
- Financial (transfers, invoices, tax notices)

Output: Max 5 bullet points. If nothing urgent, say "Inbox quiet — nothing urgent."

### Section 2b: CHAT RED FLAGS (Last 24 hours)

**Sourced from a deterministic classifier, not preview heuristics.**
Reading last-message previews and guessing state is unreliable — build a
small classifier that reads full thread bodies and applies deterministic
rules (last-message direction, question markers, artifact types,
time/money references). This is NOT included; see INTEGRATION.md for the
shape of `grok.py`-style classifier you'd write.

**Step 2b.1 — fetch and assemble.** Get the unread chat list, then fetch
each substantive chat's recent thread in parallel:

```
chats = <chat_mcp>.list_chats(limit=30, only_unread=True)

threads = parallel([
    <chat_mcp>.get_thread(chat=c.id, limit=20)
    for c in chats
])

payload = {"chats": [
    {"id": c["id"], "name": c["name"], "is_group": c["is_group"],
     "thread": t["messages"]}
    for c, t in zip(chats, threads)
]}
Write("/tmp/gt-chat.json", json.dumps(payload))
```

**Step 2b.2 — run your classifier:**

```bash
python3 $CHAT_CLASSIFIER_DIR/classify.py --input /tmp/gt-chat.json
# Writes $CHAT_CLASSIFIER_DIR/headlines.md and updates a small state db
```

The output has four buckets in priority order:
- **You owe a reply** (`awaiting_you`) — surface these
- **Conversational (low stakes)** — surface 1-2 max if recent
- **Ball in their court** (`awaiting_them`) — drop unless several days silent
- **Noise (emoji / reaction)** — never surface

**Step 2b.3 — render Section 2b.** Read `headlines.md`, extract the "You
owe a reply" bucket. Max 4 bullets.

**Bonus — feeds the verifier.** The Step 0 verifier can pick up the chat
classifier's state db as its chat-outbound source when present, so an
outbound message can auto-close a "send X to Y" todo line with no extra
wiring.

**Scope rule**: never publish chat content to a wiki / Slack / PRs /
commits — keep it in the brief only. For personal-sensitive threads,
surface as "Active thread with X, needs reply" without quoting body.

Output: max 4 lines from the `awaiting_you` bucket, one glanceable line per
person. If empty, say "🟢 Chat quiet."

### Section 2c: CONTACT STATE (classifier — NOT rendered as a table)

Aggregate email (§2) + chat (§2b) + today's calendar attendees (§1) into an
internal per-person state. This is a classifier, not a rendered table — it
feeds two card lanes:

- **`awaiting_you`** → the card's **💬 REPLIES OWED** names + the Detail
  chat/inbox lines. Newest first.
- **`awaiting_them`** → the card's **⏳ WAITING ON** lane (§2e).
- **`scheduled`** → only surfaces if it lands in the next 3 days (📆 NEXT).
- **`cold`** (>7d silent) → dropped unless high-stakes and overdue.

**Reply-owed guard.** Before putting anyone in `awaiting_you` / REPLIES
OWED, confirm there is NO outbound message from you AFTER that person's
last inbound — check ALL message types, not just text (a reply can be a
voice note, reaction, call, or media). If you've responded since, the
person is `awaiting_them` or closed, never owed. A truncated thread is not
evidence of silence: if the last message shown is inbound but the thread
is long, fetch more before classifying.

Classify each person by last-message direction + content. <CUSTOMISE>:
cross-reference your own durable memory files here (project notes, not the
todo file) so a bare name resolves to the right thread — keep that mapping
in your own config, not in this skill file.

Do NOT emit a table. The names flow straight into the card and the Detail
chat/inbox lines — once each.

### Section 2d: MONEY TODAY (feeds the card's 💸 MONEY line, optional)

A single glance line on cash movement, if that's something you track
closely. Build it from your own inputs, in priority order:

1. **Payment ground-truth dump** (`/tmp/gt-mail-pay.json`, fetched in
   §0.1): any debit/charge/decline confirmation dated today or pending.
2. **Known recurring debits** — read at runtime from your own config, do
   NOT hardcode amounts in this skill file.
3. **Bills due soon** with a date in an inbox item.

Render as ONE line: `{debit firing today} · {bill due + date} · {decline
to chase}` — or `clear today` if nothing moves. Never gross-up or invent
amounts; if a figure isn't in a source, name the item without the number.

<CUSTOMISE>: delete this section entirely if cash-flow tracking isn't part
of your brief.

### Section 2e: WAITING ON (feeds the card's ⏳ lane)

The list of things blocked on someone else, so you know what you can NOT
progress today and stop re-opening them. Source: §2c `awaiting_them` + any
Pending item whose next step is another party's reply. Names + 3-word
topic, `·`-separated, max 5. This is the antidote to re-surfacing "chase X"
every single morning when the ball is genuinely with X.

### Section 3: TRACKED METRICS (optional — price, deadline, anything)

<CUSTOMISE> entirely. The original version of this section tracked a
crypto asset's spot price plus a tax-filing countdown, read at runtime
from a personal finance file — never hardcoded. The pattern worth
keeping: **if a number changes, read it from a file at runtime; never
hardcode a number in a skill prompt**, because skills get re-read and
re-trusted every session and a stale hardcoded figure becomes a silent
lie.

A minimal worked example (price tracking via a public API, no auth
needed):

```
curl -s "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
```

Output format:
```
{ASSET}: $X.XX | 24h: +/-X.X%
```

If you have a deadline-driven obligation (a filing, a renewal, a
contract date), read the live figure from a dated file you maintain — see
`infra-templates/canonical/` in this bundle for a pattern that solves
exactly this ("derive at runtime, never hardcode a high-stakes personal
number"). Soften or suppress any section that could cause needless anxiety
on a bad day (a "red-day rule": on a down day, lead with the long-term
plan, not a bold loss figure) if that fits how you want this brief to feel.

### Section 3b: YOUR CUSTOM DAILY METRIC (optional, repeatable)

<CUSTOMISE> — this is an extension point, not a section to fill in from
this template. The original version had two of these: a financial
independence dashboard and a habit-tracking reinforcement line, each
backed by its own small Python script reading its own state file. The
pattern: a single `python3 $YOUR_SCRIPT/status.py` call, rendered as 2-3
compact lines in the brief. Add as many of these as you want, or none.

### Section 4: WEATHER

```
WebSearch: "$BRIEF_CITY weather today forecast"
```

One line: `{City}: 22°C, sunny, high 26°C. Rain at 4 PM (60%).`

<CUSTOMISE>: set `$BRIEF_CITY` to your own city.

### Section 5: PENDING ACTIONS

**Primary source of truth: `$BRIEF_VERIFIER_DIR/proposals.md`** — produced
by Section 0's verifier preflight. NEVER iterate the raw `$TODO_FILE`
unchecked lines when proposals.md is fresher than 60 seconds. The verifier
already filtered out items that ground truth shows are done.

Read `proposals.md` AND `/tmp/brief-verdict-summary.json` (produced by
Section 0.4) and process these buckets:

1. **"Verified done since last brief"** subsection (optional, only if
   non-empty): one bullet per "Proposed [x]" entry from `proposals.md`,
   PLUS one bullet per `closed` verdict from
   `/tmp/brief-verdict-summary.json`, max 4 each, format `✓ {summary} —
   {evidence}`. This is reinforcement that the system is working; keep it
   short.

2. **"Needs human review"** subsection (only if non-empty): one bullet per
   entry from `proposals.md` (rules-based ambiguity, deadline passed, file
   missing), PLUS one bullet per `ambiguous` verdict. Flag for triage.

3. **"Pending actions"** main bucket: lift directly from proposals.md
   "Still pending" entries. **Shadow mode caveat**: even if Section 0.4
   marked a claim `closed`, do NOT remove it from Pending Actions yet —
   the closed bullet at the top is informational, the pending list stays
   complete until live-mode is enabled.

Within Pending, order by urgency:
- Today's date-heading items first
- Then `Open (no date)` items
- Then overdue items (dated in the past, unchecked)

If an email scanned in Section 2 surfaces a pending action that isn't in
proposals.md OR the todo file, surface it in the brief but do NOT
auto-append. Suggest the user add it via "remind me to X" (see
`claude/rules/reminders.md`).

Hygiene: After the brief, prune `[x]` items older than 7 days silently
(except high-stakes ones — confirm first). Past-date sections with
everything ticked can be removed.

Output: numbered list, most urgent first.

### Section 5b: CROSS-SESSION STATE (optional, needs recall-db)

If you've set up `infra-templates/recall-db` (see this bundle), pull a
cross-session-working-memory snapshot: open threads, decisions logged,
file collisions across your concurrent Claude Code sessions.

```bash
python3 $RECALL_QUERY_SCRIPT status
python3 $RECALL_QUERY_SCRIPT headlines --limit 12
python3 $RECALL_QUERY_SCRIPT collisions
```

This is fleet-ops detail, not a daily-glance item by default. Compute it,
but emit a single Detail line ONLY when something is genuinely anomalous
and actionable:

- a NEW active collision in the last 30 min (two live sessions in the
  same working directory) → `🧠 collision: two sessions in {dir} —
  reconcile before editing`
- last sync run > 6h old → `🧠 brain stale — run the sync script to refresh`
- otherwise: emit NOTHING. No counts, no thread dump.

### Section 6: YESTERDAY'S REVIEW (bottom of brief, optional)

If you run a daily-review-style skill that writes a dated log file, read
yesterday's: `$BRIEF_LOG_DIR/daily-review-{yesterday-date}.md`

If it exists, extract three things only:
- The single highest-leverage lesson line
- Up to 2 rows from an "Inefficiency patterns" table, if present
- Whether there are items pending review (count only, not content)

If the file doesn't exist, skip this section entirely — do NOT surface
absence. If the file exists but is empty/malformed, skip silently.

This section is reinforcement, not a reread. Keep it to 4-5 lines max.

---

## Output Format

**Emit TWO messages, GLANCE-FIRST:**

1. **MESSAGE 1 — the `⚡ TODAY` glance card.** The 5-second read. The only
   thing you need to act on today. Send it FIRST, on its own.
2. **MESSAGE 2 — `📂 Detail`.** Everything that justifies the card. Lean:
   no duplicate tables, no cross-session-state dump. Each person/task
   appears exactly ONCE here.

**ANTI-REDUNDANCY (the #1 failure mode of a daily brief).** A name or task
in the card is a headline; its supporting line lives once in Detail. Never
list the same person in full three times. If you're repeating, collapse
it. The card points; the Detail explains.

Emoji landmarks are FIXED — do not vary them once you've settled on a set;
consistent landmarks are what make the card eye-scannable.

### MESSAGE 1 — `⚡ TODAY` glance card

No tables, no paragraphs. Short lines only (≤72 chars). Build it from:
ACT NOW ← the single highest-priority thing you can DO in ~1 minute right
now; MUST DO ← 🔴 Pending + 🔴 Inbox; REPLIES ← `awaiting_you` (§2c);
WAITING ← `awaiting_them` + blocked Pending (§2c/§2e); MONEY ← §2d if used;
NEXT ← §1 next-3-days; top strip ← weather (§4) + tracked metric (§3) if used.

**⚡ ACT NOW (one imperative top line).** The brief leads with exactly ONE
imperative, do-it-in-a-minute action. Not a list, not a lane — the single
most time-sensitive thing right now, phrased as a command you can act on
without thinking (e.g. "Reply to Sam — they're waiting on a venue
confirm", "Pay the invoice, link in inbox", "Call the dentist to confirm").
Pick it by: (1) anything live/expiring in the next hour beats (2) a today
🔴 MUST DO, beats (3) the oldest unanswered reply. If genuinely nothing is
live, write `⚡ ACT NOW  🟢 nothing live — your move is rest/keep going`.
One line, one verb, one target. Never two.

```markdown
⚡ TODAY · {Day DD Mon} · {wx emoji}{high}° · {tracked metric if used}
══════════════════════════════
⚡ ACT NOW  {one imperative, doable in ~1 min — or "🟢 nothing live"}
──────────────────────────────
🎯 MUST DO
 🔴 {hard thing — deadline today/tomorrow, money at risk, or a gate}
 🟡 {important but has a little slack}
 {or "🟢 Clear runway — nothing hard-locked today."}
──────────────────────────────
💬 REPLIES OWED ({n})
 {Name}{🎙️ if voice} · {Name} · {Name}        ← names only, newest first
──────────────────────────────
⏳ WAITING ON (can't push today)
 {who/what} · {who/what}
──────────────────────────────
💸 MONEY  {debits today / due soon / a decline — or "clear today"}  (if used)
📆 NEXT   {next notable event or deadline within 3 days}
══════════════════════════════
▾ detail below
```

If a block is genuinely empty, show its 🟢 line (e.g. `💬 REPLIES OWED (0)
🟢 none`) — never drop the landmark, so the card's shape is constant.

### MESSAGE 2 — `📂 Detail`

```markdown
# 📂 Brief detail — {Day, Month DD, YYYY} · 🕐 {clock} {tz}

## 📅 Schedule
{today timeline, mark [done]/[now]/upcoming}
Next 3 days: {one terse line per notable item}

## 📧 Inbox
{max 5 bullets · 🔴 urgent/money · 🟡 needs reply · 🟢 done/FYI · or "🟢 quiet"}

## 💬 Chat
{👉 **{Name}** — "{≤6-word gist}" · {what to do}  (🎙️ for a voice note)}
{this is the SOURCE for the card's REPLIES OWED names · max 4 · or "🟢 quiet"}

## 📊 Tracked metrics (if used)
{per §3 — derive at runtime, never hardcode}

## 🌤️ Weather
{City}: XX°C, {conditions}. High XX°C. {🌧️ rain alert if applicable}

## ✅ Other pending (not already in MUST DO)
{numbered, de-duped against the card · 🔴/🟡/🟢 by urgency}

{## 🧠 Cross-session state — ONE line, ONLY if anomalous}
{## 📋 Yesterday's review — ONLY if file valid: the one top lesson}
```

---

## Important Notes

- **MCP tools only work in main conversation** — this skill CANNOT run in
  subagents/background agents
- Keep the entire brief under ~30 lines. This is a glance, not a deep dive.
- If the user says "ultrathink", expand: read more emails in full, add a
  weekly calendar preview, include more tracked metrics
- All times in your configured timezone (`$BRIEF_TZ`)
- Convert currencies using a live rate from search results, with a
  documented fallback constant if search fails
- Don't fabricate data — if a search fails, say "couldn't fetch" rather
  than guessing
- On weekends, skip the "Schedule" section if calendar is empty and note
  "Weekend — no events"

## Scheduling

To run this automatically every morning, use the `/schedule` skill (built
into Claude Code) or a local cron job:

```
/schedule create "morning-brief" --cron "0 8 * * *" --prompt "/morning-brief"
```

This runs at 8 AM in your scheduler's timezone. Note: scheduled triggers
run as remote agents which do NOT have MCP tool access. For full MCP
integration (email, calendar), run `/morning-brief` manually or via a
local cron that invokes `claude -p "/morning-brief"`.

### Local cron alternative (full MCP access):

```bash
# Add to crontab -e:
0 8 * * * cd $BRIEF_WORKDIR && claude -p "/morning-brief" > $BRIEF_LOG_DIR/$(date +\%Y-\%m-\%d).md
```

Note: the Claude Code CLI does NOT have `--output-file` — use shell
redirection (`> file`) instead.

This saves each morning brief to a dated file for future reference.

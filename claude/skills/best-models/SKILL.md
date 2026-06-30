---
name: best-models
description: |
  Ensures your whole Claude Code setup is calling the best-of-the-best
  frontier models — and that every provider key actually works. Audits the
  model IDs hardcoded across all skills (deliberation skills, *-loop and
  *-query helpers, cross-model review) against what each provider's API
  ACTUALLY serves right now, verifies reachability with live 1-token pings,
  flags stale / invalid / dead-key references, and applies confirmed swaps
  with backups. Derives "best" live from the provider APIs + a quick web
  check — never from a hardcoded list (model rankings rot).
  Trigger: "/best-models", "best models", "are we on the best models",
  "best of the best", "model audit", "are our models current", "check our
  model access", "are we missing any model access", "update our models",
  "is our gemini/openai/grok key working".
  DO NOT activate for: picking which model to use for ONE task (just answer),
  or Claude Code harness model selection (that is /model, harness-managed).
---

# /best-models — keep the setup on the frontier

Multi-model skills hardcode provider model IDs in many files. Models ship
continuously; keys expire silently. This skill is the periodic sweep that
guarantees two things:

1. **Access** — every provider key still authenticates.
2. **Currency** — every hardcoded model ID is the best reachable one.

## Hard rules (do not violate)

- **Derive, never hardcode "best."** The truth is the provider API, checked
  at runtime. Do NOT bake a "GPT-X is best" claim into this skill — that is
  the exact stale-cluster failure mode.
- **Never `sed` skill files. Back up before any edit.** Use the Edit tool or
  a timestamped `.bak`.
- **Confirmation-gated writes.** Show the diff table, get an explicit GO
  before changing any file. Never swap a model ID silently.
- **Listed ≠ works.** Confirm a candidate with a real `probe` ping before
  recommending a swap.
- **Judgment on tier.** Do not blindly upgrade a deliberately-cheap model
  (e.g. a `*-mini` / `*-flash` used for a bulk/context task) to a flagship.
  Match tier-for-tier; flag, don't force.

## The engine

`audit.py` (same dir) does the deterministic, verifiable half. Keys load
from `~/.claude/api-keys.env`.

```
python3 audit.py list   --pretty   # what each provider API serves now
python3 audit.py scan   --pretty   # model IDs your skills currently call
python3 audit.py audit  --pretty   # full diff: OK / OLD / BAD per reference
python3 audit.py probe --provider P --model M   # 1-token live ping
python3 audit.py audit  --json     # machine output for programmatic swaps
```

Status codes in the audit: `OK` current+valid · `OLD` valid but a newer
same-tier sibling exists · `BAD` not served by the API (invalid / dead key).

## Run procedure

1. **`python3 audit.py audit --pretty`** — get the full picture.
2. **Live web check** — one `WebSearch` for the current frontier per active
   provider ("best OpenAI / xAI / Google / Anthropic model <month year>").
   This is the judgment layer the script deliberately omits. Reconcile hype
   against what the API actually serves — the API wins.
3. **Probe every proposed target** with `probe` before suggesting it. A
   swap target must return `ok: true`.
4. **Present a table**: provider · file(s) · current ID · proposed ID ·
   why · verified? Keep it ≤72 chars wide.
5. **Dead keys are an ACCESS gap, not a swap.** If a key fails auth, do NOT
   rewrite IDs for that provider — the fix is a new key. Tell the user
   exactly where to regenerate it (e.g. Gemini → aistudio.google.com/apikey)
   and that they paste it into `~/.claude/api-keys.env`. Never invent a key.
6. **On GO** — for each file, back it up (`cp f f.bak-YYYYMMDD-HHMM`) then
   Edit the ID. Group by file. Report what changed.
7. **Verify after** — re-run `audit.py audit --pretty`; the swapped refs
   should flip to `OK`. State the before/after count. No "done" without it.

## What "best" means per provider (judgment notes)

These notes reflect the model landscape at the time of writing and WILL go
stale — always reconcile against the live API + web check, never trust the
note alone.

- **OpenAI** — flagship reasoning models vs cheap mini/nano legs. Keep cheap
  legs cheap; only bump their version, not their tier.
- **xAI** — Grok ships on meme-style, not semver, versioning, so a naive
  numeric version sort can mis-order releases (e.g. read "4.20" > "4.3" when
  4.3 is actually newer). Ignore any audit hint that contradicts the
  provider's own "latest"; the live API + web check win.
- **Google** — Gemini flash vs pro tiers ship on their own cadence; re-check
  which pro tier is live before wiring it into pro slots.
- **Anthropic** — the chat models you RUN come from the Claude Code harness
  (`/model`), not the `ANTHROPIC_API_KEY`. That key is only for skills that
  call Anthropic directly. A 401 there is expected and is NOT an access gap
  for the harness models.

## Output shape

End with: (a) one-line verdict — are we on the best of the best, yes/no;
(b) the gap table; (c) any dead-key access gaps with the fix; (d) the
proposed swap set awaiting GO. Brief, not a dump.

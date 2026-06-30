# Files I write for you: always .txt, never .md

When the user asks to write, draft, or save anything to a file for
them to read or send, the file is a `.txt` file. This includes
drafts (email, WhatsApp, Slack, letters, DMs), notes, summaries,
plans, analysis, briefs — anything generated that they are meant to
read or send.

Default to `.txt`. Do not generate `.md` files unless the user
explicitly asks for markdown (e.g. "write a markdown doc", "save as
md", a project convention like memory files, or a tool that requires
it like Confluence publishing).

## Why

- `.md` opens in a markdown renderer on many setups. Good for
  reading docs, wrong for paste-into-email or paste-into-WhatsApp
  because the asterisks and pound signs come along.
- `.txt` opens in a plain text editor. No render, no surprises when
  pasting elsewhere.
- If the user paste-alls from these files into other apps, `.txt` is
  the safe default.

## How

- Write the body to a `.txt` file with a descriptive kebab-case
  name.
- Default location: `$DRAFTS_DIR` (e.g. `~/drafts/`) — use a
  relevant project subdir if one is obviously in play.
- Give the user the FULL absolute path to the file.
- Body only for sendable messages. No `To:` / `Cc:` / `Subject:`
  header lines inside the file — they bleed into the body when
  paste-alled.
- Put recipient, subject, and any send-meta in the chat, not the
  file.
- If the user has told you they don't like hyphens or em-dashes in
  prose, honor that in drafts too.

## Iterating

- When revising, edit the file in place. Do not re-paste the full
  body each turn. A one-line note on what changed is fine.

## When .md IS the right choice

- Memory/index files that a system requires as .md.
- Project documentation files that already exist as .md (don't
  convert).
- Files going to Confluence (markdown is the source format).
- Files the user explicitly asks for as markdown.
- README files in repos.

Everything else written for the user to read or send: `.txt`.

<!-- CUSTOMISE: set $DRAFTS_DIR, e.g. export DRAFTS_DIR=~/drafts.
     This rule originally hardcoded a specific user's home directory
     convention and personal formatting quirks (no hyphens) — adjust
     the "Iterating" / hyphen note to your own preference or delete
     it. -->

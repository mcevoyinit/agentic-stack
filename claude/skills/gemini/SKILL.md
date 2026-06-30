---
name: gemini
description: Get second opinions and alternative perspectives from Google's Gemini. Auto-activates when the user mentions "gemini", "ask gemini", or wants Gemini's perspective. Strong on multimodal/visual reasoning and fast iteration.
---

# Gemini Second Opinion Agent

You are an expert at leveraging Google's Gemini to provide alternative
perspectives and second opinions on technical decisions, code
implementations, and architectural choices.

**ACTIVATION**: This skill activates when the user:
- Mentions "gemini", "ask gemini"
- Says "how else could we...", "alternative approach", "different perspective"
  and wants Gemini's view
- Wants validation of an approach or implementation from Gemini
- Requests a UI/visual/multimodal judgment Gemini tends to be strong at

**DO NOT activate** for:
- Questions that don't benefit from a second opinion
- Simple factual queries better answered directly
- When the user specifically wants only Claude's opinion

---

## Your Capabilities

### Available Utility

**Script**: `~/.claude/skills/gemini/utils/gemini_query.py`

**Usage**:
```bash
python3 ~/.claude/skills/gemini/utils/gemini_query.py "<prompt>" ["<optional context>"]
```

**Returns**: Gemini's response as plain text (stdout) or error (stderr)

**Model**: set via `GEMINI_MODEL` env var, otherwise the script's own
default. <CUSTOMISE>: pin the exact model version you want in your
`CLAUDE.md` or shell profile — model availability moves fast enough
that a hardcoded default in this skill would go stale.

**Auth**: reads `GEMINI_API_KEY` from `~/.claude/api-keys.env`, then
`.env.local`/`.env`, then the environment. Never hardcode the key.

### How to Use It

When the user asks for a second opinion or alternative approach:

1. **Formulate the prompt** for Gemini with a clear question or problem
   statement, plus any relevant code/context (trim to what's load-bearing).
2. **Call the script** and capture stdout.
3. **Present Gemini's perspective** alongside your own — don't just
   relay it verbatim, synthesize: where do you agree, where do you
   differ, and why.
4. **For major/irreversible decisions**, get more than one model's
   opinion (see `gemini`, `openai`, `grok`, or run `/looper` /
   `/kamikaze` for structured multi-model deliberation).

### Failure handling

If the script errors (missing key, network failure, rate limit), say
so plainly and continue with your own analysis — never block on a
second opinion that isn't available.

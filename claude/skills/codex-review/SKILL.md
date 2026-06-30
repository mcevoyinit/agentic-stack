---
name: codex-review
description: |
  Cross-provider review using OpenAI models. Two targets: code diffs and Claude Code
  conversation transcripts. Three tiers: fast (codex-auto-review), standard (gpt-5.5
  via Codex CLI), deep (gpt-5.5-pro via API — auto-upgrades to gpt-5.5-pro via
  CODEX_REVIEW_MODEL env var when API access lands).
  Trigger: "codex review", "codex-review", "second opinion", "cross-model review",
  "openai review", "deep review", "pro review", "review this conversation",
  "run codex over this session".
---

# Codex Review: Cross-Provider Review

Run code changes OR conversation transcripts through OpenAI's best models for an independent second opinion — all from inside Claude Code.

## Model selection (auto-upgrades)

The Deep tier reads `$CODEX_REVIEW_MODEL` (default `gpt-5.5-pro`). When GPT-5.5 Pro lands on the API, set `export CODEX_REVIEW_MODEL=gpt-5.5-pro` in your shell rc — every mode below auto-upgrades. Optional helper scripts live under `${CODEX_REVIEW_DIR:-$HOME/.codex-review}` (set `CODEX_REVIEW_DIR` to wherever you keep them); e.g. `"$CODEX_REVIEW_DIR/probe.sh"` to check API availability.

## Three tiers

| Tier | Model | Method | When to use |
|------|-------|--------|-------------|
| **Fast** | `codex-auto-review` | Codex CLI (ChatGPT auth) | Routine commits, quick sanity check |
| **Standard** | `gpt-5.5` | Codex CLI (ChatGPT auth) | Complex logic, multi-file changes |
| **Deep** | `$CODEX_REVIEW_MODEL` (default `gpt-5.5-pro`, target `gpt-5.5-pro`) | OpenAI Responses API (inline curl below, or `"$CODEX_REVIEW_DIR/review.sh"`) | Security-sensitive, architecture changes, conversation reviews |

## Procedure

1. **Detect changes** — run `git diff` and `git diff --cached` to collect the diff
2. **Choose tier** — default to Fast. Use Standard for complex changes. Use Deep when user says "deep review", "pro review", or for security-sensitive code.
3. **Send to OpenAI** — use the appropriate command below
4. **Report findings** — present findings with file:line references
5. **Act on findings** — fix legitimate bugs before reporting task complete

## Commands

### Fast tier (codex-auto-review via Codex CLI):
```bash
git diff | codex exec -m codex-auto-review --skip-git-repo-check "Review this diff for bugs, security issues, and logic errors. Be concise. Only flag real problems, not style nits. Format: file:line — issue"
```

### Standard tier (gpt-5.5 via Codex CLI):
```bash
git diff | codex exec -m gpt-5.5 --skip-git-repo-check "You are a senior code reviewer. Review this diff for: 1) Logic bugs 2) Security vulnerabilities 3) Race conditions 4) Error handling gaps 5) Performance issues. Be specific with file:line references. Skip style comments."
```

### Deep tier (gpt-5.5-pro via Responses API):
```bash
DIFF=$(git diff)
curl -s https://api.openai.com/v1/responses \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg diff "$DIFF" '{
    model: "gpt-5.5-pro",
    input: ("You are an elite code reviewer. Review this diff with maximum depth.\n\nFlag:\n1. Logic bugs and off-by-one errors\n2. Security vulnerabilities (injection, auth bypass, SSRF, etc.)\n3. Race conditions and concurrency issues\n4. Error handling gaps\n5. Performance anti-patterns\n6. Data loss risks\n\nBe specific: file:line — severity — issue — fix.\nOnly flag real problems. Maximum 5 findings.\n\nDiff:\n" + $diff),
    reasoning: {effort: "high"},
    max_output_tokens: 4000
  }')"
```

The Deep tier response comes back as JSON. Extract the output text:
```bash
echo "$RESPONSE" | jq -r '.output[] | select(.type == "message") | .content[].text'
```

## Guidelines

- Default to **Fast** tier unless told otherwise
- Auto-escalate to **Standard** if the diff is >200 lines or touches auth/payment/crypto code
- Auto-escalate to **Deep** if user says "deep", "pro", "thorough", "security review"
- If no diff exists, tell the user there's nothing to review
- Only flag real problems — no style nits, no "consider adding tests" filler
- Maximum 5 findings per review
- Deep tier costs ~$0.01-0.05 per review (reasoning tokens + output). Very cheap.

## Cost reference (gpt-5.5-pro API)

- Input: $30/M tokens (~$0.003 per 100-line diff)
- Output: $180/M tokens (~$0.01 per review response)
- Typical review: **~$0.01-0.05** depending on diff size

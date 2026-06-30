---
name: agent-browser-ui-testing
description: |
  Methodology for using Vercel agent-browser CLI to systematically test UI features.
  Use when: (1) testing a new UI feature end-to-end in a browser, (2) verifying access
  control or visibility rules across multiple user sessions, (3) filling forms in React
  apps that use component libraries (Ant Design, Material UI, Shadcn), (4) collecting
  screenshot evidence of test results, (5) debugging why agent-browser interactions fail
  (stale refs, shell expansion, overlay elements). Covers the --native flag, --annotate
  screenshots, eval for React inputs, keyboard pattern for custom dropdowns, multi-session
  parallel testing, and diff-based verification.
author: Claude Code
version: 1.1.0
date: 2026-03-09
---

# Agent-Browser UI Testing Methodology

## Overview

Vercel's `agent-browser` (v0.16+) is a Rust CLI that drives Chrome via a background daemon.
It replaces Playwright scripts with composable shell commands, making it ideal for AI agents
to test UI features interactively. This skill covers **how to think about and structure**
browser-based UI testing, not just the command reference.

**CLI path** (if installed via nvm): `~/.nvm/versions/node/v20.19.2/bin/agent-browser`
If not on PATH, either use the full path or `export PATH="$PATH:$(dirname $(which node))"`

## The Testing Loop

Every UI test follows this cycle:

```
Navigate → Snapshot → Interact → Re-snapshot → Assert → Screenshot
```

**Golden rule**: Always re-snapshot after ANY DOM change (navigation, dropdown open/close,
modal appear, form submission). Stale refs cause timeout errors that look like bugs but aren't.

```bash
AB="agent-browser"

# 1. Navigate
$AB open http://localhost:3000/settings

# 2. Snapshot (get interactive element refs)
$AB snapshot -i
# Output: @e1 [tab] "Books", @e2 [tab] "Team", @e3 [button] "Create Book"

# 3. Interact
$AB click @e1

# 4. Re-snapshot (refs changed after tab switch)
$AB snapshot -i
# Output: @e1 [input] "Book Name", @e2 [select] "Type", @e3 [button] "Save"

# 5. Assert (check expected elements exist)
# If @e3 says "Save" — the tab loaded correctly

# 6. Screenshot (evidence)
$AB screenshot --annotate /tmp/test-evidence/books-tab.png
```

## Mode Selection

### When to Use `--native`

The `--native` flag enables a pure Rust daemon that talks CDP directly (no Node.js/Playwright):

```bash
# Per-command
agent-browser --native open http://localhost:3000

# Persistent (recommended for test sessions)
export AGENT_BROWSER_NATIVE=1
```

| Use `--native` when | Use default (Playwright) when |
|---------------------|-------------------------------|
| Performance-critical CI/CD | Need Firefox/WebKit testing |
| Lightweight environments (no Node) | Need Playwright-specific features |
| Chromium or Safari targets | Cross-browser matrix testing |
| Long-running test sessions | First-time setup (more stable) |

**Caveat**: Must `agent-browser close` before switching between native and default mode.

### When to Use `--headed`

```bash
export AGENT_BROWSER_HEADED=1
```

Use headed mode when:
- Debugging why a test step fails (see exactly what the browser sees)
- Demonstrating a feature to stakeholders via screen share
- Developing a new test flow (visual feedback accelerates iteration)

### When to Use `--annotate`

```bash
agent-browser screenshot --annotate /tmp/evidence.png
```

Produces a screenshot with `[N]` labels overlaid on interactive elements, mapping to `@eN` refs.
Use when:
- Generating test evidence (the annotated screenshot IS the proof)
- Debugging element targeting (see which `[N]` maps to which visual element)
- Canvas/chart elements that are invisible to text snapshots

## React & Component Library Patterns

### The Eval Pattern (React Synthetic Events)

React ignores direct `element.value = x` assignments. You must use the HTMLInputElement
prototype setter to trigger React's synthetic event system:

```bash
# WRONG: React won't see this
agent-browser eval 'document.querySelector("input").value = "test"'

# RIGHT: Triggers React's onChange handler
agent-browser eval 'const el = document.querySelector("input[type=password]"); const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set; s.call(el, "MyPassword!!"); el.dispatchEvent(new Event("input", { bubbles: true }));'
```

**When to use eval over fill**:
- Passwords with shell-hostile characters (`!!`, `$`, backticks)
- Inputs controlled by React state that ignore DOM-level changes
- Custom input components that wrap native inputs with overlays

### The Keyboard Pattern (Custom Dropdowns)

Component libraries (Ant Design, Material UI, Headless UI) render custom dropdown
overlays that block standard click interactions. The accessibility refs either point
to non-interactable overlay `<span>` elements or time out entirely.

**Fix**: Click the combobox to open it, type to filter, Enter to select:

```bash
# Click the combobox/select to open dropdown
agent-browser click @e12

# Type search text (triggers the library's filter)
agent-browser keyboard type "United States"

# Brief wait for filter to narrow results
sleep 0.5

# Press Enter to select first matching option
agent-browser press Enter
```

This pattern works universally for:
- **Ant Design**: Select, AutoComplete, Cascader
- **Material UI**: Autocomplete, Select
- **Shadcn/UI**: Combobox, Command
- **Headless UI**: Listbox, Combobox

### Form Scrolling Gotcha

Trade creation forms (or any long form in a scrollable container) don't respond to
`agent-browser scroll down 500` — that scrolls the viewport, not the form container.

**Fix**: Use `--selector` to scope scroll, or click refs directly (the browser auto-scrolls
to bring the target into view):

```bash
# Scope scroll to a container
agent-browser scroll down 500 --selector ".ant-modal-body"

# Or just click the next field — browser auto-scrolls
agent-browser click @e25
```

## Multi-Session Testing (Access Control / Multi-User)

For testing features that involve multiple users (permissions, visibility, collaboration):

```bash
# Session 1: Admin user
agent-browser --session admin open http://localhost:3000
# ... login as admin ...
agent-browser --session admin state save /tmp/auth-admin.json

# Session 2: Restricted user
agent-browser --session operator open http://localhost:3000
# ... login as operator ...
agent-browser --session operator state save /tmp/auth-operator.json

# Admin creates a resource
agent-browser --session admin click @e5    # "Create Book"
agent-browser --session admin fill @e1 "London Desk"
agent-browser --session admin click @e3    # Save

# Operator verifies visibility
agent-browser --session operator open http://localhost:3000/settings
agent-browser --session operator snapshot -i
# Assert: "London Desk" should NOT appear for restricted user
```

### State Persistence (Skip Auth on Re-runs)

```bash
# Save after first login
agent-browser state save /tmp/auth-admin.json

# Load on subsequent runs (skips entire login flow)
agent-browser state load /tmp/auth-admin.json
agent-browser open http://localhost:3000/dashboard
# Already authenticated — no redirect
```

### Auth0 / OAuth Login Pattern

```bash
# 1. Open app (redirects to Auth0)
agent-browser open http://localhost:3000
agent-browser wait --load networkidle
agent-browser snapshot -i

# 2. Fill email (standard fill works)
agent-browser fill @e1 "user@company.com"

# 3. Fill password (use eval for special chars)
agent-browser eval --stdin <<'EVALEOF'
const el = document.querySelector("input[type=password]");
const setter = Object.getOwnPropertyDescriptor(
  window.HTMLInputElement.prototype, "value"
).set;
setter.call(el, "MyP@ssword!!");
el.dispatchEvent(new Event("input", { bubbles: true }));
EVALEOF

# 4. Submit and wait for redirect
agent-browser click @e5     # "Continue" button
sleep 5                     # Auth0 processing + redirect
agent-browser wait --load networkidle

# 5. Save state for future runs
agent-browser state save /tmp/auth-state.json
```

## Verification Strategies

### Diff-Based Verification

```bash
# Take baseline snapshot BEFORE action
agent-browser snapshot -i > /tmp/baseline.txt

# Perform action
agent-browser click @e3     # e.g., "Delete Book"

# Compare — shows what changed in accessibility tree
agent-browser diff snapshot
# Output uses +/- format (like git diff)
# + [row] "London Desk" — appeared
# - [row] "Singapore Desk" — disappeared
```

### Screenshot Evidence Collection

Organize evidence by test phase:

```bash
EVIDENCE="/tmp/test-evidence/$(date +%Y%m%d-%H%M)"
mkdir -p "$EVIDENCE"

# Phase 1: Setup
agent-browser screenshot --annotate "$EVIDENCE/01-setup.png"

# Phase 2: Action
agent-browser click @e5
agent-browser screenshot --annotate "$EVIDENCE/02-after-action.png"

# Phase 3: Verification
agent-browser --session restricted snapshot -i
agent-browser --session restricted screenshot --annotate "$EVIDENCE/03-restricted-view.png"
```

### Visual Regression

```bash
# Baseline
agent-browser screenshot /tmp/baseline.png

# ... deploy change ...

# Compare
agent-browser diff screenshot --baseline /tmp/baseline.png --threshold 0.1
# Output: mismatch %, diff image with red highlights
```

Threshold guide:
- `0.05` — pixel-perfect (catches anti-aliasing)
- `0.1` — reasonable CI default
- `0.2` — catches major layout shifts only

## Common Failures & Fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `click @e5` times out | Stale ref (DOM changed) | Re-snapshot: `snapshot -i` |
| `click --ref eN` times out on React elements | agent-browser click dispatches at element center but React synthetic events may not fire | Use JS eval: `eval 'document.querySelector("[data-x]").click()'` |
| "element may be blocked" | Component library overlay | Use keyboard pattern instead |
| "Wrong email or password" | Shell ate `!!` in password | Use `eval` with heredoc |
| Snapshot shows old page | Navigation not complete | Add `wait --load networkidle` |
| Form field doesn't update | React ignores DOM assignment | Use eval with prototype setter |
| Scroll doesn't reach element | Scrolling viewport, not container | Use `--selector` or click ref |
| Session conflict | Previous daemon still running | `agent-browser close` first |
| `--native` commands fail | Mixed mode (native + default) | Close and restart in one mode |
| SyntaxError in eval | Smart quotes or shell escaping | Write JS to file, eval via `"$(cat /tmp/script.js)"` |

### React Table Row Click (TanStack / Ant Design)

React table rows (TanStack Table, Ant Design) use `<div>` elements with `onClick` handlers
bound via React's synthetic event system. **Native `click --ref` often times out**, but
JS eval `.click()` works:

```bash
# FAILS: agent-browser click dispatches pointer events that React may not capture
agent-browser click --ref e15    # → timeout

# WORKS: Direct JS click triggers React's synthetic event system
agent-browser eval 'document.querySelector("[data-contract-no]").click()'
```

**Why**: React 18's event delegation attaches handlers at the root, not on individual elements.
The `element.click()` method dispatches a `click` event that bubbles to the root and gets
captured by React. Agent-browser's coordinate-based click sometimes misses due to virtual
row rendering or overlay elements.

### Shell Escaping: Write JS to File

When eval strings contain quotes, special chars, or complex logic, write to a temp file:

```bash
cat > /tmp/my-eval.js << 'JSEOF'
var btns = document.querySelectorAll("button");
for (var i = 0; i < btns.length; i++) {
  if (btns[i].textContent.indexOf("Edit Blotter") >= 0 && !btns[i].disabled) {
    btns[i].click();
    break;
  }
}
JSEOF
agent-browser eval "$(cat /tmp/my-eval.js)" --session seller
```

This avoids: zsh `!!` expansion, smart quote corruption, nested quote conflicts.

### Password with `!!` via Python Subprocess

For passwords containing `!!` (zsh history expansion), use Python to invoke agent-browser:

```python
import subprocess
pw = 'MyPass1234!!'
js = f'var e=document.querySelector("input[type=password]");' \
     f'var s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set;' \
     f's.call(e,"{pw}");e.dispatchEvent(new Event("input",{{bubbles:true}}))'
subprocess.run(['agent-browser', 'eval', js, '--session', 'seller'], timeout=15)
```

## Integration with API Tests

Browser tests prove the **UI renders correctly**. API tests prove the **security model works**.
Use both:

```
API tests (fast, 5s):
  - Book scope enforcement
  - Cross-namespace isolation
  - Role-based access control
  - Dual-namespace write consistency

Browser tests (slower, 2-5 min):
  - Form validation UX
  - Tab visibility for roles
  - Dropdown population
  - Modal interactions
  - Visual evidence for stakeholders
```

**Pattern**: Run API tests first (fast feedback), then browser tests for UI proof.
If API tests pass but browser tests fail, the bug is in the UI layer, not the server.

## Test Structure Template

```bash
#!/bin/bash
# Feature: [Feature Name]
# Date: $(date +%Y-%m-%d)
AB="agent-browser"
EVIDENCE="/tmp/test-evidence/feature-name-$(date +%H%M)"
mkdir -p "$EVIDENCE"

# --- SETUP ---
$AB state load /tmp/auth-admin.json 2>/dev/null || {
  # Login flow here if no saved state
  $AB open http://localhost:3000
  # ... auth steps ...
  $AB state save /tmp/auth-admin.json
}

# --- PHASE 1: Precondition ---
$AB open http://localhost:3000/target-page
$AB wait --load networkidle
$AB snapshot -i
$AB screenshot --annotate "$EVIDENCE/01-precondition.png"
# Assert: expected elements visible

# --- PHASE 2: Action ---
$AB click @e5
$AB wait --load networkidle
$AB snapshot -i
$AB screenshot --annotate "$EVIDENCE/02-action.png"
# Assert: expected result

# --- PHASE 3: Cross-user Verification ---
$AB --session restricted state load /tmp/auth-restricted.json
$AB --session restricted open http://localhost:3000/target-page
$AB --session restricted wait --load networkidle
$AB --session restricted snapshot -i
$AB --session restricted screenshot --annotate "$EVIDENCE/03-restricted.png"
# Assert: restricted user sees/doesn't see expected data

# --- CLEANUP ---
$AB close
$AB --session restricted close
echo "Evidence collected in $EVIDENCE"
```

## Notes

- **Token efficiency**: ~800 tokens per snapshot vs ~10K+ for Playwright MCP (90% reduction)
- **Ref lifecycle**: Refs (`@e1`, `@e2`) are session-scoped and invalidated on DOM change
- **`find text` pitfall**: `find text "Submit" click` fails if multiple elements match.
  Use refs from snapshot instead, or narrow with `find role button --name "Submit"`
- **Sleep timings**: React state updates need ~0.3-0.5s after interactions. Auth0 redirects
  need ~3-5s. Blockchain writes need ~5-10s. Prefer explicit waits over fixed sleeps.
- **CI/CD**: Use `--native` + headless (default) + named sessions. Auto-detects Docker.
  Always `close` sessions to prevent leaked Chrome processes.

## References

- [agent-browser GitHub](https://github.com/vercel-labs/agent-browser) — 17K stars, Rust CLI
- [agent-browser Changelog](https://agent-browser.dev/changelog) — version history
- [agent-browser Diffing Guide](https://agent-browser.dev/diffing) — visual regression
- Command reference: `.claude/skills/agent-browser/SKILL.md`

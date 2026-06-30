---
name: x-bookmark-export-cdp
description: |
  Programmatic X/Twitter bookmark export using Chrome DevTools Protocol (CDP).
  Use when: (1) user wants to export X bookmarks without manual browser steps,
  (2) hardcoded bearer tokens or query IDs return 401/404 errors against X's
  internal GraphQL API, (3) building repeatable scripts to fetch X data that
  survive API credential rotation. Covers CDP network interception, Chrome
  cookie profile copying, and X's GraphQL bookmark pagination.
author: Claude Code
version: 1.0.0
---

# X/Twitter Bookmark Export via Chrome DevTools Protocol

> This skill documents a reusable technique. It drives YOUR OWN logged-in X
> session via your local Chrome profile — no account handle or credentials
> are embedded. The "import endpoint" referenced below is a generic stand-in
> for whatever store you push the exported JSON into; with `--export-only`
> the script just writes a JSON file and imports nothing.

## Problem
X's internal GraphQL API requires a bearer token and query ID (QID) that rotate
without notice. Tools that hardcode these values break silently. Additionally,
Chrome's cookie database is encrypted with macOS Keychain keys, so copying
cookies to a Playwright/Puppeteer profile doesn't transfer auth. AppleScript
`execute javascript` in Chrome can't handle async/await (returns before the
Promise resolves).

## Context / Trigger Conditions
- Bearer token returns 401 against X's `/i/api/graphql/` endpoints
- Query ID returns 404 (X changed the operation's QID)
- Need to export X bookmarks programmatically without manual browser steps
- A bookmarklet or hardcoded credentials have gone stale
- AppleScript approach returns `missing value` for async JS execution

## Solution

### Architecture
Launch a **separate Chrome instance** with `--remote-debugging-port`, using a
temp copy of the user's Chrome profile (only Cookies file). Connect via
WebSocket CDP. Use `Network.enable` to intercept live API requests and discover
current credentials automatically.

### Step-by-step

1. **Copy Chrome cookies to temp profile:**
   ```javascript
   cpSync(join(CHROME_PROFILE, 'Default', 'Cookies'), join(TEMP_DIR, 'Default', 'Cookies'));
   cpSync(join(CHROME_PROFILE, 'Local State'), join(TEMP_DIR, 'Local State'));
   ```
   The encryption key reference in `Local State` allows the temp Chrome to decrypt cookies.
   Resolve `CHROME_PROFILE` from `$CHROME_PROFILE` (default
   `$HOME/Library/Application Support/Google/Chrome`) — never hardcode a user path.

2. **Launch Chrome with remote debugging:**
   ```bash
   /Applications/Google Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9234 \
     --user-data-dir=/tmp/x-export-chrome-profile \
     --no-first-run --no-default-browser-check --disable-extensions \
     https://x.com/home
   ```
   This runs alongside the user's existing Chrome (different user-data-dir).

3. **Connect via CDP WebSocket:**
   ```javascript
   const targets = await (await fetch('http://localhost:9234/json')).json();
   const page = targets.find(t => t.url.includes('x.com'));
   const ws = new WebSocket(page.webSocketDebuggerUrl);
   ```

4. **Enable network monitoring and navigate to bookmarks:**
   ```javascript
   ws.send(JSON.stringify({ id: 1, method: 'Network.enable', params: {} }));
   // Listen for Network.requestWillBeSent events
   // Navigate: evaluate('location.href = "https://x.com/i/bookmarks"')
   // Capture the GraphQL request to /graphql/{QID}/Bookmarks
   ```

5. **Extract credentials from the intercepted request:**
   - `Authorization` header → bearer token
   - URL path → `/graphql/{QID}/Bookmarks` → query ID
   - URL query params → `features=` → feature flags

6. **Paginate bookmarks using discovered credentials:**
   Use `Runtime.evaluate` with `awaitPromise: true` to run async JS in the page
   context. Fetch 100 bookmarks per page, follow `TimelineTimelineCursor` with
   `cursorType: 'Bottom'` for pagination.

### Key gotchas

| Approach | Why it fails |
|----------|-------------|
| Hardcoded bearer token | X rotates tokens; returns 401 |
| Hardcoded query ID | X changes QIDs per deploy; returns 404 |
| Copying Chrome Cookies file to Playwright | Works! But only with `Local State` copied too |
| AppleScript `execute javascript` with async | Returns `missing value` — can't await Promises |
| Regex-searching `<script src>` tags for QID | QID lives in lazy-loaded chunks not in initial HTML |
| Intercepting fetch via JS hook then navigating | Page reload clears the hook |
| CDP `Network.enable` + navigate | Works — captures real request with all credentials |

### Bearer token extraction (fallback)
If network interception doesn't work, the bearer token can be found in X's main
JS bundle at `abs.twimg.com/responsive-web/client-web/main.*.js`:
```javascript
const t = await (await fetch(scriptSrc)).text();
const m = t.match(/Bearer ([A-Za-z0-9%]+)/);
```

## Verification
- Script outputs `Fetched N bookmarks` with N > 0
- JSON backup file created in the working directory
- If wired to an import endpoint, it returns `imported: N`

## Example
```bash
# Full automated run (export + optional import)
node fetch-bookmarks.mjs

# Export only (write JSON, no import)
node fetch-bookmarks.mjs --export-only
```

Implement the full pattern in one Node script: profile copy → Chrome launch →
CDP connect → credential discovery → bookmark pagination → (optional import) →
cleanup. Companion skill `/x-bookmarks-iterate` consumes the exported JSON.

## Notes
- Chrome must be installed at `/Applications/Google Chrome.app`
- The temp Chrome instance opens visibly (not headless) because X may block
  headless browsers. Can be minimized.
- Rate limiting: 500ms delay between pagination requests avoids throttling
- Cookie copy works because the macOS Keychain decryption key is tied to the
  user account, not the Chrome instance
- If the user is not logged in, the script waits for manual login in the temp
  Chrome window, then continues automatically
- Resolve the Chrome profile path from `$CHROME_PROFILE` / `$HOME`; do not bake
  in an absolute user path

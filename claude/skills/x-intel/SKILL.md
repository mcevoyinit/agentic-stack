---
name: x-intel
description: |
  Read-only X/Twitter intelligence gathering via the XMCP server. Produces
  structured briefs for topic sentiment, user profiles, curated watchlist
  scans, specific post analysis, and trending topics. Every mode has a
  defined API call budget to respect X API rate limits. Never takes write
  actions (no posting, liking, following, DMing — refuses even if asked).
  Trigger: "/x-intel", "x intel", "search x for", "what's twitter saying about",
  "x sentiment on", "x profile for", "watchlist scan", "x trending".
  DO NOT activate for: General web search (use WebSearch), posting to X
  (refuse — read-only only), X account management, or anything that
  requires user-context OAuth (bearer token auth only supports public data).
version: 1.0.0
---

# X Intel — Read-Only X/Twitter Intelligence

> The signal layer on top of XMCP. Turns raw X API tool calls into structured
> intelligence briefs. Rate-aware, engagement-weighted, no fabrication.

## Activation

```
ACTIVATE when user says:
  "/x-intel [anything]", "x intel [topic]", "search x for [topic]",
  "what's twitter saying about [topic]", "x sentiment on [topic]",
  "x profile for [@user]", "watchlist scan", "x watchlist",
  "x trending", "analyze this post [url]"

DO NOT activate for:
  - General web search → use WebSearch
  - "Post this to X" → REFUSE (read-only skill)
  - "Like/follow/DM" → REFUSE (read-only skill)
  - User timeline or mentions → bearer token can't access those
```

## Prerequisites

- XMCP server running on `http://127.0.0.1:8976/mcp` (launchd managed)
- X MCP tools available as `mcp__x__<operationId>` in the current session
  (tools only load at session start — if unavailable, tell user to restart)
- Read-only allowlist active: `searchPostsRecent`, `getPostsById`,
  `getUsersByUsername`, `getUsersPosts`, `getUsersFollowing`,
  `getUsersFollowers`, `getPostsLikingUsers`, `getPostsRepostedBy`,
  `getPostsQuotedPosts`, `getTrendsByWoeid`, `searchUsers`, `getNews`,
  `searchNews`, and related read endpoints

## Pre-Flight Check

Before making any MCP call, verify the X tools are available in the session.
If a tool call fails with "tool not found" or similar:

```
X tools are not loaded in this session. The XMCP server config is registered,
but MCP tools only load at session start. Please restart Claude Code and
re-run this command.
```

Also check server health if a call times out:
```bash
curl -s -o /dev/null -w "%{http_code}" -H "Accept: text/event-stream" http://127.0.0.1:8976/mcp
```
400 = server alive (needs proper MCP handshake). Connection refused = server
down; tell the user to check launchd: `launchctl list | grep xmcp`.

---

## Mode Auto-Detection

Parse the user's query and route to the appropriate mode:

| Query pattern | Mode | Example |
|--------------|------|---------|
| Starts with `@handle` | User Intel | `/x-intel @naval` |
| Contains `user:handle` | User Intel | `/x-intel user:balajis` |
| Contains `watchlist` | Watchlist Scan | `/x-intel watchlist` |
| URL with `/status/` | Post Analysis | `/x-intel https://x.com/foo/status/123` |
| Contains `post:ID` | Post Analysis | `/x-intel post:1234567890` |
| Contains `trending` | Trending | `/x-intel trending crypto` |
| Anything else | Topic Sentiment | `/x-intel Solana network outage` |

Explicit override prefixes: `topic:`, `user:`, `post:`, `watchlist`, `trending`.

---

## Mode 1: Topic Sentiment

**Purpose:** What is X saying about a topic right now? Produces a signal-over-noise brief.

**MCP calls (budget: 1-2):**
1. `mcp__x__searchPostsRecent` with the query
   - Params: `query` (the topic), `max_results: 50` (or whatever the tool allows), `tweet.fields: "public_metrics,author_id,created_at,lang"`
   - If available: `expansions: "author_id"` and `user.fields: "verified,public_metrics,username"` to enrich with author data
2. **Only if a surprising/unknown account keeps surfacing** — one `mcp__x__getUsersByUsername` for context

**Analysis protocol:**
- Filter out: retweets without added context, posts from sub-100-follower accounts, spam, posts in languages the user doesn't speak (default: keep English + Portuguese)
- Rank remaining posts by engagement ratio: `(likes + 2*reposts + 3*quotes) / max(follower_count, 100)`
- Group posts by narrative thread:
  - **Bullish** (price up, fundamentals improving, bullish catalysts)
  - **Bearish** (price down, risks, warnings)
  - **News/Announcement** (factual updates, partnerships, launches)
  - **Rumor/Speculation** (unsourced claims, leaks)
  - **Shitpost/Noise** (exclude from analysis)
- Identify "key voices": verified accounts OR >10K followers OR high engagement ratio
- Count posts per thread; determine dominant sentiment
- Flag contradictions: if the same claim has both bullish and bearish framings from credible accounts

**Output format:**
```markdown
## X Intel: [topic] — Topic Sentiment
API calls: [N] | Posts scanned: ~[M] | Filtered to: [K] signal posts

### Summary
[2-3 sentences. What is the dominant narrative? Who is driving it? Any surprises or contradictions?]

### Sentiment: [Bullish / Bearish / Neutral / Mixed]
[1-2 sentence reasoning. Include rough distribution, e.g. "60% bullish, 25% neutral, 15% bearish among credible voices"]

### Key Posts
| Account | Followers | Post (truncated to ~120 chars) | ❤️ / 🔄 / 💬 | Signal |
|---------|-----------|--------------------------------|--------------|--------|
| @user1  | 45K       | "..."                          | 120/45/12    | Bullish catalyst |

### Themes
- **[Theme 1]**: [N posts] — [1-sentence summary]
- **[Theme 2]**: [N posts] — [1-sentence summary]

### Notable Absences
[Any voices you'd expect to be posting that are silent? E.g. "@SomeProject official account has not posted in 3 days despite price moving 10%"]

### Raw Query
`searchPostsRecent(query="[...]", max_results=[N])`
```

---

## Mode 2: User Intel

**Purpose:** Who is this person on X? What do they post about? Do they have reach?

**MCP calls (budget: 2-3):**
1. `mcp__x__getUsersByUsername` — profile data
   - Params: `username` (strip any leading `@`)
   - Fields: `user.fields: "description,created_at,public_metrics,verified,verified_type,location,url"`
2. `mcp__x__getUsersPosts` — recent posts
   - Params: `id` (from step 1), `max_results: 20`, `tweet.fields: "public_metrics,created_at,referenced_tweets"`
   - Exclude: `replies` (unless user explicitly asked)
3. **Optional** `mcp__x__getUsersFollowing` — network (only if user explicitly asks for network analysis or says "deep")
   - Params: `id`, `max_results: 50`

**Analysis protocol:**
- Compute follower/following ratio (high ratio = influence; low ratio = broadcaster or new account)
- Account age from `created_at`
- Posting cadence: total posts / days active (or posts in last 30 days if available)
- Theme extraction: manually scan the 20 most recent posts, cluster into 3-5 recurring topics
- Engagement quality: avg(likes + reposts) per post. Flag if below 10 despite >5K followers ("shouting into void")
- Network signal (if fetched): cluster following list by visible industry/topic

**Output format:**
```markdown
## X Intel: @[username] — User Profile
API calls: [N]

### Profile
- **Name:** [display name] [✓ if verified]
- **Handle:** @[username]
- **Bio:** "[full bio text]"
- **Followers:** [X] | **Following:** [Y] | **Ratio:** [X/Y]
- **Joined:** [date] ([X years/months on platform])
- **Location:** [if set]
- **Posts total:** [X]

### Recent Activity (last 20 non-reply posts)
**Posting cadence:** [active/dormant] — ~[N] posts/week
**Avg engagement:** [likes/post] likes, [reposts/post] reposts
**Engagement health:** [strong / adequate / weak — "shouting into void"]

### Top Themes
1. **[Theme 1]** — [N posts] — [1-sentence summary]
2. **[Theme 2]** — [N posts] — [1-sentence summary]
3. **[Theme 3]** — [N posts] — [1-sentence summary]

### Notable Recent Posts
| Date | Post (truncated) | ❤️ / 🔄 | Insight |
|------|-------------------|---------|---------|
| YYYY-MM-DD | "..." | 245/67 | [why it matters] |

### Network Signal
[If getUsersFollowing was called: clusters of who they follow, e.g. "Mostly follows DeFi founders (~40%), VCs (~25%), and crypto media (~15%)". Otherwise: "Network analysis skipped — ask for 'deep' to include."]

### Assessment
[1-2 sentences. Who is this person based on observed data? What do they care about? Is their account active and engaged or dormant/broadcast-only?]
```

---

## Mode 3: Watchlist Scan

**Purpose:** What are my curated accounts talking about right now?

**Prerequisite:** A watchlist file at `~/.claude/x-watchlist.md`. If it doesn't exist, create it with the starter template (see bottom of this file). If it exists but is empty, tell the user to add accounts.

**MCP calls (budget: 2N where N = accounts scanned, CAPPED at 8 accounts = 16 calls):**
For each account on the watchlist (up to 8):
1. `mcp__x__getUsersByUsername` to resolve handle → ID
2. `mcp__x__getUsersPosts` for latest 5 non-reply posts

**Pre-execution warning:** Before making any calls, output:
```
Watchlist scan will make ~[2N] API calls ([N] accounts × 2 calls each).
On free tier (100 user lookups/month, 10 searches/month), this is [X]% of
monthly user lookup budget. Proceed? (default: yes, cap at 8 accounts)
```
Only skip the warning if user explicitly said "just run it" or similar.

**Analysis protocol:**
- For each account: extract the most recent 1-2 notable posts (highest engagement) and the dominant theme
- Cross-reference themes across accounts: if 2+ accounts are discussing the same thing, that's a cluster — call it out
- Flag anomalies: account that normally posts daily is silent, or an account posted 10x more than usual
- Group output by watchlist category (from the file structure)

**Output format:**
```markdown
## X Intel: Watchlist Scan
API calls: [N] | Accounts scanned: [X] of [Y total] | Date: [YYYY-MM-DD]

### 📊 Cross-Cutting Signals
[Most important section — what are MULTIPLE accounts talking about?]
- **[Cluster topic 1]**: [N accounts] — [1-sentence summary]
- **[Cluster topic 2]**: [N accounts] — [1-sentence summary]

### [Category 1 from watchlist file, e.g. "Crypto"]

**@account1** ([followers]) — [cadence: active/dormant]
- Latest: "[most notable post truncated]" ([likes]❤️ [reposts]🔄)
- Theme: [1-line summary of recent posting]
- [⚠️ Flag if anomaly, e.g. "Silent for 5 days — unusual"]

**@account2** ([followers]) — [cadence]
- ... (same structure)

### [Category 2, e.g. "Professional"]
[Same structure]

### [Category 3, e.g. "General Intel"]
[Same structure]

### 🎯 Action Items
[Max 3 bullets. What should the user actually do based on this scan?]
```

---

## Mode 4: Post Analysis

**Purpose:** What's the discourse around a specific post? Who's amplifying it and what are they saying?

**Input parsing:** Extract post ID from the URL (`https://x.com/user/status/ID` → ID) or from `post:ID` prefix.

**MCP calls (budget: 2-3):**
1. `mcp__x__getPostsById` — the post itself
   - Params: `id`, `tweet.fields: "public_metrics,created_at,author_id,referenced_tweets,entities"`, `expansions: "author_id"`, `user.fields: "verified,public_metrics,username"`
2. `mcp__x__getPostsQuotedPosts` — quote tweets (the real discourse; replies require different endpoint that may not be available with bearer token)
   - Params: `id`, `max_results: 20`, `tweet.fields: "public_metrics,author_id"`, `expansions: "author_id"`
3. **Optional** `mcp__x__getPostsLikingUsers` — who amplified it (skip unless user says "deep" or engagement is unusually high)

**Analysis protocol:**
- Context: what does the post actually say? Who wrote it? Are they credible (verified, high followers)?
- Virality signal: `quotes / likes` ratio. High ratio (>5%) = controversial. Low ratio (<1%) = consensus or engagement farming.
- Quote tweet themes: agreement, disagreement, mockery, amplification, correction
- Notable engagers: verified or >10K follower accounts that liked/quoted
- Sentiment of quotes: majority bullish or bearish on the post's claim?

**Output format:**
```markdown
## X Intel: Post Analysis
API calls: [N]

### Original Post
**@[user]** ([followers] followers) [✓ if verified] — [date]
> "[full post text]"

**Engagement:** [X]❤️ · [Y]🔄 · [Z]💬 · [W] views
**Quote/Like ratio:** [X%] — [consensus / mixed / controversial / astroturfed]

### Discourse (from [N] quote tweets)
- **[Theme 1]** ([X]% of quotes) — "[representative quote]" (@user, [likes])
- **[Theme 2]** ([X]% of quotes) — "[representative quote]" (@user, [likes])
- **[Theme 3]** ([X]% of quotes) — "[representative quote]" (@user, [likes])

### Notable Engagers
[Verified or high-follower accounts — max 5]
- @user1 ([followers]) — [liked / quoted saying "..."]

### Signal
[1-2 sentences. What does the engagement pattern actually tell us? Is this a consensus view, a contested claim, a viral shitpost, or an astroturfed amplification?]
```

---

## Mode 5: Trending

**Purpose:** What's hot on X right now, optionally filtered by domain.

**MCP calls (budget: 1-2):**
1. `mcp__x__getTrendsByWoeid` — trending topics
   - Params: `woeid: 1` (worldwide) or a specific location WOEID if requested
   - Common WOEIDs: 1 (worldwide), 23424977 (US), 44418 (London), 23424916 (Portugal)
2. **Optional** `mcp__x__searchPostsRecent` on one specific trend for context — only if user asked about a particular trend

**Analysis protocol:**
- Raw list: top 10 trends with tweet volumes
- If user specified a domain (e.g. `trending crypto`): manually filter trends that match the domain (keyword heuristic) — don't fabricate relevance
- Flag promoted trends separately

**Output format:**
```markdown
## X Intel: Trending
API calls: [N] | Region: [Worldwide / US / etc]

### Top Trends
| # | Trend | Tweet Volume | Category |
|---|-------|--------------|----------|
| 1 | #foo | 125K | Politics |
| 2 | #bar | 80K | Sports |
| ... | | | |

### [Domain] Filter (if user specified)
[Trends that relate to the domain, with 1-line context for each]

### Signal
[1 sentence: anything unusual? E.g. "Crypto trends dominated by #SOL after a major announcement"]
```

---

## Rate Limit Awareness

Every output ends with:
```
---
**Rate budget used this call:** [N] API calls
**Current tier:** [unknown — check developer.x.com/en/portal/products]
**Free tier limits:** 10 searches/month, 100 user lookups/month, 10K posts/month
```

If the user says "check rate limits" or asks how much budget they've used,
honestly say we don't track persistent usage — each invocation reports its
own call count, and X's own dashboard has the authoritative numbers.

---

## Design Principles

1. **Minimum API calls per mode.** Never exceed the stated budget without explicit user permission.
2. **Signal over noise.** Engagement metrics + follower counts + verification status are the credibility proxy. Filter ruthlessly.
3. **Never fabricate.** If a tool returns empty results, say "no posts found." Don't invent data.
4. **No write actions.** If the user says "and like the top post" or "post this summary" or "follow @user", REFUSE. This skill is read-only. Tell them:
   > This skill is read-only by design. The XMCP allowlist excludes write operations (posting, liking, following, DMs) to avoid risking account suspension under X's current AI-interaction enforcement. If you want write actions, set up a dedicated account and use the safety-focused `x-autonomous-mcp` server instead.
5. **Graceful degradation.** If a tool fails, say so with the error. Don't silently fall back to fabricated output.
6. **Bearer-only awareness.** Some endpoints (user timeline, mentions, DMs) require OAuth user context. XMCP runs in bearer-only mode. If a tool returns a 401/403, say: "This endpoint requires OAuth user context and is not available in bearer-only mode."
7. **Respect the user's language.** Default to the user's languages (configurable). User can override with "all languages" or specify.

---

## Integration with Other Skills

This skill is designed to be called from other skills:

### From a morning-brief style skill
A daily brief may call this in Topic Sentiment mode with a query like "[TICKER] OR [project]" for an overnight X pulse. Return a compact 2-3 bullet summary, not the full brief format.

### From a deep-research skill
Called in Topic Sentiment mode with broader topic-related queries. Return full brief format as one input to the overall research output.

### From `/person-research`
Called in User Intel mode for the X/Twitter profile ingestion phase. Return User Intel brief tagged `[SELF-REPORTED]` since X bios are curated self-narrative.

### Compact mode
When called from another skill, detect via the invocation context and produce compact output (3-5 bullets max) instead of the full brief format. The full brief is for direct invocation.

---

## Example Invocations

```
"/x-intel Solana"
  → Topic Sentiment mode. Search "Solana OR SOL" recent posts.

"/x-intel @naval"  
  → User Intel mode. Profile + recent posts for @naval.

"/x-intel user:balajis deep"
  → User Intel mode WITH network analysis (adds getUsersFollowing call).

"/x-intel watchlist"
  → Load ~/.claude/x-watchlist.md, scan up to 8 accounts, produce grouped brief.

"/x-intel https://x.com/ethereum/status/1234567890"
  → Post Analysis mode. Fetch post + quote tweets.

"/x-intel trending"
  → Worldwide trending topics.

"/x-intel trending crypto"
  → Worldwide trends filtered for crypto keywords.

"/x-intel" (no args)
  → Show usage help. List the 5 modes with one example each.
```

---

## Starter Watchlist Template

If `~/.claude/x-watchlist.md` doesn't exist when watchlist mode runs, create it with:

```markdown
# X Watchlist

> Curated accounts for `/x-intel watchlist` scans.
> Max 8 accounts per category recommended to stay within rate budget.
> Order matters — first 8 accounts across all categories are scanned.

## Crypto
- @VitalikButerin
- @balajis

## Professional
- @paulg
- @sama

## General Intel
- @naval
- @pmarca
```

Ask the user to edit and add their preferred accounts after creation.

---

## Structural Limitations

Include in every output footer:

1. **Read-only by design.** No write operations possible through this skill.
2. **Bearer-only auth.** Some endpoints (user timeline, mentions, DMs) are unavailable.
3. **Rate limits are real.** Free tier: 10 searches/month, 100 user lookups/month. Check developer.x.com for current usage.
4. **X enforcement risk.** As of 2026, X is cracking down on AI-interaction even for read-only automation. If API calls start returning 429s unexpectedly, the account may be rate-limited or flagged.
5. **No persistent cache.** Every invocation hits the API fresh. Save important findings to notes if you need them later.
6. **Bias warning.** X's algorithmic surfacing and post visibility affects what `searchPostsRecent` returns. Treat as a sample, not a census.

---
name: cheap-flights
description: |
  Find the cheapest flights between any two cities using real tools and techniques
  that actually work — not viral AI slop prompts. Searches Google Flights, Skiplagged,
  Kiwi, and airline sites. Applies: nearby airports, split ticketing, hidden city,
  fare calendar analysis, points optimization, and credit card portal arbitrage.
  Trigger: "cheap flights", "find flights", "book flights", "flight search",
  "how much to fly", "flights to", "flights from", "flight deal", "fare search".
  DO NOT activate for: general travel planning without flight search, hotel booking,
  car rental, or train tickets.
version: 1.3.0
---

# Cheap Flights — Real Fare Intelligence

> Airlines have 24-77 discrete fare buckets per flight with $100+ gaps between them.
> Pricing is set by bureaucratic yield management, not omniscient algorithms.
> The edge comes from searching wider (more routes, dates, airports) and smarter
> (split tickets, hidden city, fare class awareness) — not from magic prompts.

## Activation

```
ACTIVATE when user says:
  "cheap flights", "find flights", "book flights", "flight search",
  "how much to fly to", "flights to X", "flights from X", "fare search",
  "flight deal", "cheapest way to fly", "/cheap-flights"

DO NOT activate for:
  - General trip planning without flight component
  - Hotel/accommodation searches
  - Train or bus alternatives (unless comparing)
  - "What airline should I fly" without price context
```

## Input

Collect from user (ask if not provided):
- **Origin**: City/airport code (ask the user — no default; set your own home airport if you want one, e.g. `JFK`)
- **Destination**: City or region
- **Dates**: Specific dates, flexible range, or "anytime in [month]"
- **Passengers**: Number (default: 1). If 10+, trigger group fare path
- **Flexibility**: Can dates shift ±3 days? Open to nearby airports?
- **Constraints**: Carry-on only? Need checked bags? Loyalty program preference?
- **Budget**: Hard ceiling or "as cheap as possible"

---

## Search + Booking Architecture (8 Layers)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FARE INTELLIGENCE ENGINE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 0: PROGRAMMATIC PROBE   fast-flights → Google Flights    │
│  ────────────────────          (always run first; fastest)      │
│                                                                  │
│  Layer 1: DIRECT SEARCH        Skyscanner / Kayak cross-check   │
│  ────────────────────                                            │
│                                                                  │
│  Layer 2: NEARBY AIRPORTS      ±150km radius, secondary hubs    │
│  ────────────────────                                            │
│                                                                  │
│  Layer 3: SPLIT TICKETING      Two one-ways, mixed carriers     │
│  ────────────────────                                            │
│                                                                  │
│  Layer 4: HIDDEN CITY          Skiplagged connections            │
│  ────────────────────          (carry-on only, one-way only)    │
│                                                                  │
│  Layer 5: FARE CALENDAR        ±7 day window, cheapest combo    │
│  ────────────────────                                            │
│                                                                  │
│  Layer 6: POINTS & PORTALS     Award seats, portal pricing      │
│  ────────────────────                                            │
│                                                                  │
│  Layer 7: BOOKING (design)     Cart-to-payment, human confirms  │
│  ────────────────────          Duffel + browser automation      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Execution Protocol

### Layer 0: Programmatic Probe (fast-flights)

**Always run this first.** It's the fastest way to get a structured baseline
straight from Google Flights, with airline names, times, durations, stops,
and prices — no API key, no scraping framework, no WebSearch latency.

The skill ships with a self-contained venv and a CLI wrapper:

```bash
# One-way
~/.claude/skills/cheap-flights/.venv/bin/python \
  ~/.claude/skills/cheap-flights/scripts/search.py JFK LAX 2026-05-01

# Round-trip
~/.claude/skills/cheap-flights/.venv/bin/python \
  ~/.claude/skills/cheap-flights/scripts/search.py JFK LAX 2026-05-01 \
    --return 2026-05-15

# Filters
search.py JFK LAX 2026-05-01 --adults 2 --seat business --max-stops 0
search.py JFK LAX 2026-05-01 --top 15            # show more rows
search.py JFK LAX 2026-05-01 --json              # machine-readable for piping
```

Output is a markdown table sorted by price, with airline / departure /
arrival / duration / stops / price columns and a "cheapest" summary line.

**For fare calendar arbitrage (Layer 5)**, loop the script across a date
range:

```bash
for d in 2026-04-28 2026-04-29 2026-04-30 2026-05-01 2026-05-02; do
  search.py JFK LAX "$d" --json | jq '{date:"'"$d"'", min:(.flights|min_by(.price_value).price_raw), market:.current_price}'
done
```

#### Caveats — read these before quoting any number to the user

1. **Currency follows IP geolocation.** Google returns BRL when called from
   Brazil, EUR from Portugal, etc. The wrapper parses currency into a
   `price_currency` field but does NOT convert. Always quote prices with the
   currency symbol intact.
2. **fast-flights v2.2 + local patches (fixed 2026-06-10).** `search.py`
   monkeypatches the library: fetch sends the yt-dlp SOCS consent cookie
   (EU IPs otherwise get the "Before you continue" wall = 0 rows) and uses
   `impersonate="chrome"` (primp ≥1.2 dropped `chrome_126`); parsing falls
   back to aria-labels when Google A/B-serves a layout that breaks the
   library's class selectors. Don't `pip install -U` without re-verifying
   a known-good route (e.g. JFK LAX) shows airline/time/duration, not just price.
3. **`--max-stops 0` raises if no nonstops exist.** The wrapper catches this
   and prints a hint. Drop or raise the flag.
4. **Duplicate-looking rows are real.** Google often returns the same flight
   multiple times under different fare basis codes — ranking by price is fine.
5. **Treat as a probe, not a booking source.** Fares change hourly. Verify on
   google.com/travel/flights before recommending the user pull the trigger.
6. **Bootstrap (only if the venv is missing or broken):**
   ```bash
   python3 -m venv ~/.claude/skills/cheap-flights/.venv
   ~/.claude/skills/cheap-flights/.venv/bin/pip install -r \
     ~/.claude/skills/cheap-flights/requirements.txt
   ```

### Layer 1: Direct Search Cross-Check

Once Layer 0 gives you a baseline, cross-check on aggregators that
fast-flights doesn't cover (low-cost carriers, self-transfer routing):

```
WebSearch: "[origin] to [destination] flights [dates] Skyscanner"
WebSearch: "[origin] to [destination] flights [dates] Kayak"
WebSearch: "[origin] to [destination] flights [dates] kiwi.com"
```

Use these to **invalidate or strengthen** the Layer 0 number — if Skyscanner
shows €40 cheaper, that's usually a low-cost carrier Google Flights hides.

### Layer 2: Nearby Airports

Search alternate airports within ~150km of both origin and destination.

**Worked example — finding alternates for a metro origin (here, NYC):**
- A secondary airport within the same metro (e.g. EWR alongside JFK/LGA)
- A low-cost-carrier hub 1-3h away by train/bus, often much cheaper
- A larger hub a short connection away with a deeper route network
- A neighboring-region airport reachable by a cheap rail link

Apply the same logic to whatever origin the user gives you. **For both
the origin and any destination**, search:
```
WebSearch: "airports near [destination city]"
WebSearch: "[nearby airport] to [destination] flights [dates]"
```

### Layer 3: Split Ticketing

Check if two separate one-way tickets (potentially on different airlines) beat the round-trip:

```
WebSearch: "[origin] to [destination] one way [outbound date]"
WebSearch: "[destination] to [origin] one way [return date]"
```

Also check mixed-carrier combinations:
- Outbound on low-cost (Ryanair, easyJet, Wizz Air)
- Return on legacy carrier (or vice versa)

Kiwi.com specializes in this:
```
WebSearch: "kiwi.com [origin] [destination] [dates]"
```

### Layer 4: Hidden City (Skiplagged)

**IMPORTANT CONSTRAINTS — state these clearly to user:**
- Carry-on luggage ONLY (checked bags go to ticketed destination)
- ONE-WAY tickets only (airline cancels return if you skip a leg)
- Risk of airline account/loyalty points cancellation (rare but real)
- Not suitable for connecting flights where you check bags

```
WebSearch: "skiplagged [origin] [destination] [dates]"
WebFetch: https://skiplagged.com/flights/[origin_code]/[dest_code]/[date]
```

Search for flights where [destination] is a CONNECTION, not the final stop:
```
WebSearch: "flights through [destination] from [origin] cheapest"
```

### Layer 5: Fare Calendar Analysis

Find the cheapest day to fly within a flexible window:

```
WebSearch: "Google Flights fare calendar [origin] to [destination] [month]"
WebSearch: "cheapest day to fly [origin] to [destination] [month year]"
```

Key timing principles (from Berkeley EMSRb research):
- **Book 21+ days out** — prices jump at 21, 14, and 7 day marks
- **Tuesday/Wednesday departures** tend cheapest for leisure routes
- **Saturday night stay** on round-trips drops the fare (signals leisure, not business)
- **Red-eye flights** are systematically cheaper
- **6 AM departures** underpriced because business travelers avoid them

### Layer 6: Points & Portal Optimization

If user has loyalty program balances or travel credit cards:

```
WebSearch: "[airline] award availability [origin] [destination] [dates]"
WebSearch: "[credit card] travel portal [origin] [destination] flights"
```

**Points transfer partners to check:**
- Amex → multiple airlines (transfer, don't book through portal)
- Chase UR → United, Hyatt, Southwest, others
- TAP Miles&Go → Star Alliance award space

**Portal arbitrage**: Chase, Amex, Capital One portals sometimes show prices
10-30% below direct booking, PLUS earn bonus points.

### Layer 7: Booking — bundled `scripts/hermes` CLI

The skill ships a self-contained, Duffel-backed booking CLI under
`scripts/`. It is optional: search (Layers 0-6) works without ever
booking. The booking surface assembles a cart up to the payment page,
then hands off to a human (see "Posture" below).

It exposes these operations (Duffel-backed where the carrier supports
NDC; browser automation for low-cost carriers):

- search   — Duffel offer-request, ranked by price
- quote    — re-fetch an offer for its current price
- hold     — hold-order (no card), returns a PNR
- services — list/attach available bags or seats on a held order

Config lives entirely under `~/.config/cheap-flights/` (override with the
`CHEAP_FLIGHTS_CONFIG_DIR` env var if you want a different location):
API keys in `.env` (mode 600), passenger profile in
`passenger_profile.json` (mode 600), confirmations in `confirmations/`.
Never commit any of these — they are gitignored by default.

**Entry point: `scripts/hermes`** (executable shell wrapper).

```
hermes whoami                      # config status
hermes key set <duffel_test_...>   # persist API key to ~/.config/cheap-flights/.env (600)
hermes profile init                # interactive passenger setup wizard
hermes profile show                # print profile (redacted)
hermes search ORIG DEST DATE       # parallel Duffel + Google search
hermes book ORIG DEST DATE         # search → pick → hold (interactive)
hermes quote OFFER_ID              # re-quote a Duffel offer
hermes hold OFFER_ID               # hold an existing offer (skip search)
```

**Lessons from the v1 build** — bake these into v2:

1. **Duffel test mode only reliably holds against the synthetic
   `Duffel Airways` carrier.** Iberia/AA/BA test offers report
   `requires_instant_payment: false` but return `invalid_order_create_type`
   when you actually POST a hold. Real carriers in live mode behave
   correctly; sandbox just has narrower hold coverage. Don't burn time
   debugging — try a different offer.
2. **Phone numbers must be in E.164 international format.** Bare
   country code without proper subscriber digits (e.g. `+351900000000`)
   returns `invalid_phone_number`. Use a real verified number.
3. **Offers expire in ~minutes.** Don't cache offer IDs between sessions.
   Re-search every time; quote before hold.
4. **fast-flights fixed 2026-06-10** (consent cookie + robust parser,
   patches live in this skill's `scripts/search.py`). If you add a
   separate Playwright-based Google scraper, parse aria-labels rather
   than fragile class selectors — Google A/B-serves layouts.
   **Duffel offers come from TEST mode** unless a `duffel_live_key` is
   configured — test-mode prices/airlines are synthetic; never quote
   them to the user as real fares.
5. **The Vueling-style "instant-pay (v2)" tag** in the hermes output
   means the offer requires immediate card payment and v1 (hold-only)
   can't handle it. v2 needs Duffel Payment Intents to cover these.

**Posture: cart-to-payment, human confirms 3DS.** The skill assembles the
booking up to the payment page, then stops. The user taps pay and handles
Strong Customer Authentication (SCA / 3D Secure). Rationale:

- Fully autonomous booking with a stored card is a footgun for personal
  travel — one stale fare, one wrong PAX name, one mis-clicked bag add and
  you eat €115+ in change fees with no recourse.
- EU SCA effectively forces a human in the loop for card-not-present
  payments anyway.
- The 80/20 win is automating fare-pick + passenger autofill + ancillary
  selection. Payment is 30 seconds; the rest is 10 minutes per booking.

#### Routing (by carrier)

| Carrier class | Path | Notes |
|--------------|------|-------|
| Legacy / flag (TAP, Aer Lingus, BA, Iberia, AF, KLM, LH, etc.) | Duffel API | NDC offers, hosted payment widget, real PNR returned |
| Ryanair | Browser automation | API-blocked. Drive ryanair.com checkout via Playwright/agent-browser. Stop at payment page. |
| easyJet | Browser automation | Same as Ryanair. Limited Duffel coverage. |
| Wizz / Vueling | Browser automation | Same. |
| Award / points | Manual | No API path. Print deep-link to airline award portal. |
| Hidden city (Skiplagged) | Manual | Print Skiplagged URL. Never auto-book — TOS risk. |

Dispatch by IATA carrier code in `references/carrier_routing.md` (to be
created at build time). Default = manual deep-link if uncertain.

#### Components to build

```
scripts/
  book.py                 # dispatcher: takes offer_id, routes to backend
  book_duffel.py          # Duffel offer → order, stop before payment auth
  book_browser.py         # Playwright runner, one driver module per LCC
  drivers/
    ryanair.py            # Ryanair-specific checkout walk
    easyjet.py
    wizz.py
    vueling.py
  profile.py              # load/validate passenger profile
references/
  carrier_routing.md      # IATA code → backend mapping
  passenger_profile.example.json
```

User data lives at `~/.config/cheap-flights/passenger_profile.json`
(gitignored, file mode 600). Schema: name as on passport, DOB, passport
number + expiry + country, nationality, frequent-flyer numbers per
alliance, contact email + phone. **Never** card details — those stay in
the browser keychain / Duffel hosted widget.

#### Duffel path (legacy carriers)

1. `offer_request` with origin/dest/dates/PAX from search result
2. Pick offer by `offer_id` (the one the user selected from Layer 0 output)
3. `offer` re-quote — fares change between search and book; abort if delta
   > €5 without confirming
4. Create `order` with passenger data from profile
5. Return Duffel hosted-payment URL → open in browser → user pays
6. Poll `order` for `payment_status` → on success, save PNR + ticket numbers
   to `~/.config/cheap-flights/confirmations/YYYY-MM-DD_<PNR>.json`

Duffel sandbox is free and works end-to-end with test cards. Live mode
requires a business entity (sole-trader registration is enough) and
Duffel's compliance onboarding. Plan: sandbox first, decide on live later.

#### Browser-automation path (low-cost carriers)

Reuse the `agent-browser-ui-testing` skill's methodology. Per-carrier
driver does:

1. Navigate to airline.com flight search
2. Fill origin/dest/dates (carriers vary — some need keyboard pattern for
   custom dropdowns; see agent-browser-ui-testing skill notes)
3. Pick outbound + return matching the search result (verify price within
   €5 tolerance)
4. Decline upsells aggressively unless `--with-bag` / `--with-seat` flags
   set in profile
5. Fill passenger data from profile
6. **STOP at payment page.** Print "ready to pay" + screenshot path.
   User completes payment + 3DS manually.
7. After user confirms paid, optionally re-attach to scrape PNR from
   confirmation page.

Brittleness budget: expect each driver to break ~quarterly on UI changes.
Acceptable — these are 50-line scripts, not products.

#### Safety rules (non-negotiable)

- **Re-quote before submit.** Fare from search ≠ fare at checkout. Abort
  if discrepancy > €5 without explicit user confirmation.
- **Name exactness.** Passenger name must match passport character-for-
  character. Ryanair charges €115 for name corrections; the skill must
  fail loud if profile name has special characters that the carrier UI
  might mangle.
- **No card storage.** Browser keychain or Duffel hosted widget only.
- **Confirmation artifacts.** On success, save: PNR, ticket numbers,
  confirmation email (forward to your own address), and a PDF
  of the confirmation page to `~/.config/cheap-flights/confirmations/`.
- **Two-step confirm.** Before clicking "pay" on Duffel hosted widget or
  before browser-automation hits payment page, print full summary
  (route, times, PAX, price, bag, seat) and require user to type
  `yes book` to proceed.
- **No silent retries.** If booking fails (sold out, payment declined,
  3DS timeout), surface the error immediately. Do not re-try with a
  different offer — fares may have moved.

#### Open decisions (resolve at build time)

- Duffel sandbox vs live — start sandbox. Live needs business entity.
- Browser-automation harness: agent-browser CLI (Vercel) vs raw Playwright
  vs Stagehand. Lean: agent-browser, the `agent-browser-ui-testing`
  skill already documents its quirks.
- Passenger profile encryption: file-mode 600 + macOS FileVault is
  probably enough for a personal tool. Revisit if multi-user.
- Multi-passenger bookings: out of scope for v1. v1 = single-PAX or
  pre-known group from profile.

---

## Group Bookings (10+ Passengers)

When searching for 10+ passengers, switch to group fare protocol:

1. **DO NOT search retail pricing for full group** — airlines show higher prices for large groups
2. **Search for 1 passenger** to get baseline per-person price
3. **Contact airline group desk directly:**
   ```
   WebSearch: "[airline] group booking desk phone number"
   ```
4. Group fares are typically 10-25% below retail for 10+ pax
5. Group fares include: flexible name changes, sometimes free bags, single invoice
6. **Deadline**: Request 6-8 weeks before travel minimum

Example — find the relevant carrier's group desk for your origin:
```
WebSearch: "[your main carrier] group booking request"
```

---

## Output Format

Present findings as a structured comparison:

```markdown
## Flight Search: [Origin] → [Destination]
**Dates**: [dates] | **Passengers**: [N] | **Searched**: [date]

### Best Options Found

| Option | Route | Price | Carrier | Notes |
|--------|-------|-------|---------|-------|
| Cheapest | JFK→MDW | $87 | Frontier | Carry-on only |
| Best value | JFK→ORD | $129 | United | Checked bag included |
| Split ticket | JFK→DTW / DTW→JFK | $62+$54 | Spirit/Delta | Mix carriers |
| Hidden city | JFK→ORD(→DEN) | $71 | United | Skip DEN leg, carry-on only |
| Points | JFK→ORD | 12,500 mi | Star Alliance | Transfer partner |

### Baseline Comparison
- **Google Flights direct**: $189
- **Best found**: $71 (hidden city) / $87 (no tricks)
- **Savings**: $118 (62%) / $102 (54%)

### Booking Recommendations
1. [Primary recommendation with reasoning]
2. [Alternative if constraints change]

### Risks & Trade-offs
- [Any hidden city caveats]
- [Bag restrictions]
- [Cancellation/change flexibility]
```

---

## Key Principles

1. **Always verify prices** — WebSearch results are directional. Tell user to click through and confirm before booking.
2. **State all trade-offs** — Hidden city saves money but limits bags. Split tickets mean two separate bookings (one delay = your problem).
3. **Don't oversell savings** — If the route only saves €15, say so. Don't manufacture drama.
4. **Time-sensitive** — Fares change hourly. Stamp every search with current date and note prices are snapshots.
5. **EU261 awareness** — For EU flights, note that passenger rights (compensation for delays/cancellations) apply per-ticket. Split tickets = two separate protections (or gaps).

---

## Reference: Fare Bucket Basics

Airlines price in discrete buckets, not continuous curves:

| Code | Class | Typical Use | Flexibility |
|------|-------|------------|-------------|
| Y | Full economy | Fully flexible, walk-up | Full refund, free changes |
| B, M | Discounted economy | Standard booking | Changeable, penalty |
| Q, N | Deep discount | Early booking, sales | Non-refundable |
| X, E | Basic economy | Lowest tier | No changes, no bags |

The letter codes matter because:
- **Upgrade eligibility**: Only certain fare classes qualify
- **Mileage earning**: Basic economy (X/E) often earns 0 miles
- **Change flexibility**: Paying €20 more for an M fare vs N can save €200 in change fees

Use ITA Matrix (matrix.itasoftware.com) to see fare classes before booking.

---

## Anti-Patterns (What NOT to Do)

- **Don't use ChatGPT to "find" fares** — it can't access live pricing data
- **Don't clear cookies/use VPN** — airlines moved to server-side pricing years ago, this is cargo cult
- **Don't wait for prices to "drop"** — Berkeley research shows prices only go up as departure approaches
- **Don't book through random OTAs** to save €5 — if something goes wrong, the airline won't help you
- **Don't skiplag on round-trips** — the return gets cancelled
- **Don't fully automate payment** — stop at the payment page and let the human approve. SCA / 3DS makes headless EU card payment unreliable anyway, and the failure modes (wrong PAX name, stale fare, accidental ancillary) are too expensive for a "just trust the script" flow.
- **Don't skiplag with checked bags** — they go to the ticketed destination

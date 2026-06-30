# Flight Search Tools & Techniques Reference

## Tier 0: Programmatic (in-skill)

| Tool | How | Best For |
|------|-----|----------|
| `scripts/search.py` | `~/.claude/skills/cheap-flights/.venv/bin/python ...` | Fast structured Google Flights probe — airline / time / duration / stops / price. Always run first. |

Wraps `fast-flights` (pinned to v2.1; v2.2 has a broken parser). No API key,
no Playwright, no WebSearch latency. Runs in its own venv at
`~/.claude/skills/cheap-flights/.venv` so it doesn't pollute project envs.

See SKILL.md → Layer 0 for invocation, flags, and caveats (currency follows
IP geolocation, etc).

## Tier 1: Primary Search Engines

| Tool | URL | Best For |
|------|-----|----------|
| Google Flights | google.com/travel/flights | Fare calendar, explore map, price tracking |
| Skyscanner | skyscanner.net | "Everywhere" search, month-view calendar |
| Kayak | kayak.com | Price forecasting, flexible date matrix |
| Momondo | momondo.com | Same backend as Kayak, sometimes different results |

## Tier 2: Specialist Tools

| Tool | URL | Best For |
|------|-----|----------|
| Skiplagged | skiplagged.com | Hidden city fares |
| Kiwi.com | kiwi.com | Split-carrier combos, self-transfer routes |
| ITA Matrix | matrix.itasoftware.com | Fare class analysis, calendar view, power users |
| AwardHacker | awardhacker.com | Points transfer route optimization |
| Going.com | going.com | Mistake fares, deal alerts (paid, worth it) |
| Secret Flying | secretflying.com | Error fares, flash sales |

## Tier 3: Airline Direct (Often Cheapest)

Low-cost carriers usually don't show on aggregators:
- **Ryanair** — ryanair.com
- **easyJet** — easyjet.com
- **Wizz Air** — wizzair.com
- **Transavia** — transavia.com
- **Vueling** — vueling.com
- **Spirit / Frontier** — spirit.com / flyfrontier.com (US ultra-low-cost)

Check whichever low-cost carriers are based at or fly to your home airport.

## Key Techniques

### Hidden City Ticketing
- Book A→C with layover at B (your real destination)
- Skip the B→C leg
- **Rules**: Carry-on only, one-way only, no loyalty number, no frequent flier accrual
- **Risk level**: Low (one known ban case ever), but against airline ToS

### Split Ticketing
- Book outbound and return as separate one-way tickets
- Can mix airlines: low-cost carrier out, legacy carrier back
- **Risk**: If outbound is delayed and you miss your separate return, no protection
- **Mitigation**: Leave buffer between legs, or buy travel insurance

### Positioning Flights
- Fly from a cheaper nearby airport, even if it means an extra flight
- Example: ORIGIN→HUB ($40 low-cost) + HUB→DEST ($250 legacy) = $290 vs ORIGIN→DEST direct at $500

### Fare Calendar Arbitrage
- Google Flights date grid shows price for every day combination
- Shifting departure by 1-2 days often saves 30-50%
- Tuesday/Wednesday departures, Saturday night stays = cheapest

### Credit Card Portal Arbitrage
- Book through card travel portal for bonus points
- Chase UR portal, Amex Travel, Capital One Travel
- Sometimes portal price < airline direct price
- Stack: portal discount + points earning + card travel protections

### Error/Mistake Fares
- Airlines occasionally publish wrong prices (fat-finger errors)
- Going.com and Secret Flying monitor for these
- Window to book is usually 2-6 hours before correction
- Airlines honor ~70% of mistake fares (especially EU-originating)

## Home-Airport Intelligence (build your own)

This section is a template. Fill it in for YOUR home airport once, then
reuse it. The methodology, not the specific airports, is the value.

### Best Low-Cost Routes from [YOUR AIRPORT]
- List which low-cost carriers are based at or serve your home airport,
  and the regions each one covers cheaply.

### Loyalty Sweet Spots
- Note the award programs you hold and their best-value redemptions
  (e.g. a specific long-haul business-class route for X miles).
- List the transfer partners that feed those programs.

### Nearby Airport Alternatives
- List secondary airports within ~1-5h by car/train/short-hop, with the
  travel time and which carriers/routes each one adds. Often a hub a short
  connection away has a far deeper route network and cheaper fares.

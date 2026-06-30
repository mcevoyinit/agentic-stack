#!/usr/bin/env python3
"""
search.py — programmatic Google Flights probe for the cheap-flights skill.

Wraps fast-flights v2.2 with two local patches (see _patched_fetch and
_parse_response_robust below): consent-cookie fetch + aria-label parser.
Designed to be called by the skill or directly from a terminal.

Usage:
    search.py JFK LAX 2026-05-01                           # one-way
    search.py JFK LAX 2026-05-01 --return 2026-05-15       # round-trip
    search.py JFK LAX 2026-05-01 --adults 2 --seat business
    search.py JFK LAX 2026-05-01 --max-stops 0             # nonstop only
    search.py JFK LAX 2026-05-01 --json                    # machine-readable
    search.py JFK LAX 2026-05-01 --top 10                  # show top N

Notes:
  * Currency is whatever Google's IP geolocation chooses (BRL in Brazil,
    EUR in Portugal, etc). Currency is shown verbatim in the price string.
  * 2026-06-10: upgraded to v2.2; rich fields restored via local
    parser patch (aria-label fallbacks). EU consent wall bypassed
    via SOCS cookie. Do not remove _apply_fetch_patch().
  * `--max-stops 0` raises "No flights found" if the route has no nonstops;
    we handle that and exit cleanly with a note.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from datetime import date

from fast_flights import FlightData, Passengers, get_flights

# Google's consent wall accepts this SOCS value (same one yt-dlp ships).
# fast_flights.Cookies.new() generates a SOCS protobuf Google now rejects
# ("Before you continue" page, zero results) — do not switch back to it.
_CONSENT_COOKIES = {
    "SOCS": "CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMwODI5LjA3X3AxGgJlbiACGgYIgLC_pwY",
    "CONSENT": "PENDING+987",
}


def _patched_fetch(params: dict):
    """Replacement for fast_flights.core.fetch.

    Two fixes (2026-06-10):
      * primp >= 1.2 renamed impersonation profiles; 'chrome_126' no longer
        exists and falls back to 'random', which Google sometimes blocks.
        'chrome' is the current valid name.
      * EU IPs get Google's cookie-consent interstitial instead of results,
        so the parser sees zero flights. The SOCS consent cookie above
        skips the interstitial.
    """
    import fast_flights.core as _core

    client = _core.Client(impersonate="chrome", verify=True)
    res = client.get(
        "https://www.google.com/travel/flights",
        params=params,
        cookies=_CONSENT_COOKIES,
    )
    assert res.status_code == 200, f"{res.status_code} Result: {res.text_markdown}"
    return res


def _parse_response_robust(res):
    """Replacement for fast_flights.core.parse_response.

    Google A/B-serves layouts; on some variants the library's class-based
    selectors (div.sSHqwe.tPgKwe.ogfYpf etc.) match nothing while prices
    still parse, yielding rows with blank airline/times. aria-label
    attributes are semantic and stable across variants, so each field
    falls back to them. Result rows are deduped (Google repeats the
    best-flights block).
    """
    import re as _re

    from selectolax.lexbor import LexborHTMLParser

    from fast_flights.schema import Flight, Result

    parser = LexborHTMLParser(res.text)
    flights, seen = [], set()

    wrappers = parser.css('div[jsname="IWWDBc"], div[jsname="YdtKid"]')
    if not wrappers:
        wrappers = [parser.root]

    for i, fl in enumerate(wrappers):
        is_best_block = fl.attributes.get("jsname") == "IWWDBc" or (
            not fl.attributes and i == 0
        )
        for item in fl.css("ul.Rk10dc li"):
            labels = " ~ ".join(
                n.attributes.get("aria-label") or "" for n in item.css("[aria-label]")
            )

            def _css_text(sel):
                n = item.css_first(sel)
                return n.text(strip=True) if n else ""

            def _label(pattern):
                m = _re.search(pattern, labels)
                return m.group(1).strip() if m else ""

            name = _css_text("div.sSHqwe.tPgKwe.ogfYpf span") or _label(
                r"flights? with ([^.~]+?)\s*[.~]"
            )
            departure = _css_text("span.mv1WYe div:nth-of-type(1)") or _label(
                r"Departure time: ([^.~]+)\."
            )
            arrival = _css_text("span.mv1WYe div:nth-of-type(2)") or _label(
                r"Arrival time: ([^.~]+)\."
            )
            duration = _css_text("li div.Ak5kof div") or _label(
                r"Total duration ([^.~]+)\."
            )
            stops_txt = _css_text(".BbR8Ec .ogfYpf") or (
                "Nonstop" if "Nonstop" in labels else _label(r"(\d+ stops?) flight")
            )
            price = _css_text(".YMlIz.FpEdX") or _label(
                r"From (\d[\d,.]*) ([A-Za-z ]*dollars?|euros?|pounds?)"
            )
            ahead = _css_text("span.bOzv6")
            delay = _css_text(".GsCCve") or None

            try:
                stops_fmt = 0 if stops_txt == "Nonstop" else int(stops_txt.split(" ", 1)[0])
            except (ValueError, AttributeError):
                stops_fmt = "Unknown"

            key = (name, departure, arrival, price, duration)
            if key in seen or not (price and price != "0"):
                continue
            seen.add(key)
            flights.append(
                Flight(
                    is_best=is_best_block,
                    name=name,
                    departure=departure.replace(" ", " ").replace("\xa0", " "),
                    arrival=arrival.replace(" ", " ").replace("\xa0", " "),
                    arrival_time_ahead=ahead,
                    duration=duration,
                    stops=stops_fmt,
                    delay=delay,
                    price=price.replace(",", ""),
                )
            )

    if not flights:
        raise RuntimeError("No flights found:\n(robust parser: zero rows)")

    current_price = ""
    cp_node = parser.css_first("span.gOatQ")
    if cp_node:
        current_price = cp_node.text(strip=True).lower()
    return Result(current_price=current_price or "typical", flights=flights)


def _apply_fetch_patch() -> None:
    import fast_flights.core as _core

    _core.fetch = _patched_fetch
    _core.parse_response = _parse_response_robust


_apply_fetch_patch()


PRICE_RE = re.compile(r"([^\d\s]+)\s*([\d,.]+)")


def parse_price(price_str: str) -> tuple[str, float] | tuple[str, None]:
    """Split 'R$3771' / '$869' / '€450' into (currency, numeric)."""
    if not price_str:
        return ("", None)
    m = PRICE_RE.match(price_str.strip())
    if not m:
        return (price_str, None)
    currency = m.group(1).strip()
    raw = m.group(2).replace(",", "")
    try:
        return (currency, float(raw))
    except ValueError:
        return (currency, None)


def valid_date(s: str) -> str:
    try:
        date.fromisoformat(s)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD: {e}")
    return s


def build_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Probe Google Flights via fast-flights (pinned v2.1).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("origin", help="3-letter IATA code, e.g. JFK")
    p.add_argument("destination", help="3-letter IATA code, e.g. GRU")
    p.add_argument("date", type=valid_date, help="Departure date YYYY-MM-DD")
    p.add_argument("--return", dest="return_date", type=valid_date,
                   help="Return date for round-trip (YYYY-MM-DD)")
    p.add_argument("--adults", type=int, default=1)
    p.add_argument("--children", type=int, default=0)
    p.add_argument("--infants-in-seat", type=int, default=0)
    p.add_argument("--infants-on-lap", type=int, default=0)
    p.add_argument("--seat", default="economy",
                   choices=["economy", "premium-economy", "business", "first"])
    p.add_argument("--max-stops", type=int, default=None,
                   help="0 = nonstop only, 1 = max one stop, etc.")
    p.add_argument("--top", type=int, default=8,
                   help="How many results to show in markdown mode (default 8)")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON instead of markdown")
    return p.parse_args()


def fetch(args: argparse.Namespace):
    flight_data = [
        FlightData(
            date=args.date,
            from_airport=args.origin.upper(),
            to_airport=args.destination.upper(),
        )
    ]
    if args.return_date:
        flight_data.append(
            FlightData(
                date=args.return_date,
                from_airport=args.destination.upper(),
                to_airport=args.origin.upper(),
            )
        )
        trip = "round-trip"
    else:
        trip = "one-way"

    return get_flights(
        flight_data=flight_data,
        trip=trip,
        passengers=Passengers(
            adults=args.adults,
            children=args.children,
            infants_in_seat=args.infants_in_seat,
            infants_on_lap=args.infants_on_lap,
        ),
        seat=args.seat,
        max_stops=args.max_stops,
    )


def render_markdown(args: argparse.Namespace, result) -> str:
    flights = result.flights
    trip_label = "round-trip" if args.return_date else "one-way"
    header = (
        f"## {args.origin.upper()} → {args.destination.upper()}  "
        f"({trip_label}, {args.seat})\n\n"
        f"**Depart:** {args.date}"
    )
    if args.return_date:
        header += f" · **Return:** {args.return_date}"
    header += (
        f" · **Pax:** {args.adults}A"
        + (f"+{args.children}C" if args.children else "")
        + f"\n\n**Market:** {result.current_price} "
        f"(vs historical) · **Results:** {len(flights)}\n"
    )

    if not flights:
        return header + "\n_No flights returned._\n"

    # Sort by numeric price (ascending), keeping unparseable at the end
    def sort_key(f):
        _, n = parse_price(f.price)
        return (n is None, n if n is not None else 0)

    flights_sorted = sorted(flights, key=sort_key)
    top = flights_sorted[: args.top]

    rows = ["", "| # | Airline | Depart | Arrive | Duration | Stops | Price | Best |",
            "|---|---------|--------|--------|----------|-------|-------|------|"]
    for i, f in enumerate(top, 1):
        rows.append(
            f"| {i} | {f.name or '—'} | {f.departure or '—'} "
            f"| {f.arrival or '—'} | {f.duration or '—'} "
            f"| {f.stops if f.stops != 'Unknown' else '?'} "
            f"| {f.price or '—'} | {'★' if f.is_best else ''} |"
        )

    # Cheapest summary line
    cheapest = top[0]
    cur, num = parse_price(cheapest.price)
    cheap_line = f"\n**Cheapest:** {cheapest.price}"
    if cheapest.name:
        cheap_line += f" on {cheapest.name}"
    if cheapest.duration:
        cheap_line += f" · {cheapest.duration}"
    if cheapest.stops not in (None, "Unknown"):
        cheap_line += f" · {cheapest.stops} stop(s)"

    note = (
        "\n\n_Currency reflects Google's IP geolocation. "
        "Verify on google.com/travel/flights before booking._"
    )

    return header + "\n".join(rows) + cheap_line + note


def render_json(args: argparse.Namespace, result) -> str:
    payload = {
        "query": {
            "origin": args.origin.upper(),
            "destination": args.destination.upper(),
            "date": args.date,
            "return_date": args.return_date,
            "trip": "round-trip" if args.return_date else "one-way",
            "seat": args.seat,
            "adults": args.adults,
            "children": args.children,
            "max_stops": args.max_stops,
        },
        "current_price": result.current_price,
        "count": len(result.flights),
        "flights": [],
    }
    for f in result.flights:
        cur, num = parse_price(f.price)
        payload["flights"].append({
            "name": f.name,
            "departure": f.departure,
            "arrival": f.arrival,
            "arrival_time_ahead": f.arrival_time_ahead,
            "duration": f.duration,
            "stops": f.stops if f.stops != "Unknown" else None,
            "price_raw": f.price,
            "price_currency": cur,
            "price_value": num,
            "is_best": f.is_best,
            "delay": f.delay,
        })
    return json.dumps(payload, indent=2, ensure_ascii=False)


def main() -> int:
    args = build_args()
    try:
        result = fetch(args)
    except RuntimeError as e:
        # fast-flights raises RuntimeError("No flights found:\n...") when the
        # parser sees zero results (e.g. max_stops=0 on a route without nonstops).
        msg = str(e).split("\n", 1)[0]
        if args.json:
            print(json.dumps({"error": msg, "count": 0, "flights": []}))
        else:
            print(f"## {args.origin.upper()} → {args.destination.upper()}\n")
            print(f"_{msg}_\n")
            if args.max_stops == 0:
                print("Hint: this route may not have any nonstops. "
                      "Try removing `--max-stops 0` or raising it to 1.")
        return 2
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(render_json(args, result))
    else:
        print(render_markdown(args, result))
    return 0


if __name__ == "__main__":
    sys.exit(main())

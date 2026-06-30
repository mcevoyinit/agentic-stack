#!/usr/bin/env python3
"""Ryanair cart-to-payment driver (cheap-flights skill, Layer 7).

Walks ryanair.com from flight selection to the PAYMENT PAGE and stops.
The human reviews and pays (EU SCA/3DS requires them anyway).

Posture:
  * Headed Chromium, visible the whole time. The human can take over
    at any moment; the script never fights manual input.
  * Every step is best-effort. On failure it prints MANUAL guidance
    and keeps watching for the next page state instead of crashing.
  * Never touches card fields. Never clicks pay. No silent retries.

Usage:
  ryanair.py --origin STN --dest AGP --date 2026-06-13 \
             --depart-time 20:30 --expect-price 37.99

Profile read from ~/.config/cheap-flights/passenger_profile.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

PROFILE_PATH = os.path.expanduser("~/.config/cheap-flights/passenger_profile.json")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_profile() -> dict:
    with open(PROFILE_PATH) as f:
        p = json.load(f)
    for k in ("title", "first_name", "last_name"):
        if not p.get(k):
            sys.exit(f"profile missing {k!r} — refusing to start (name "
                     f"errors cost €115 on Ryanair)")
    return p


def try_click(page, selectors, timeout=4000, label=""):
    """Click the first selector that appears. Returns True on success."""
    for sel in selectors:
        try:
            page.locator(sel).first.click(timeout=timeout)
            log(f"OK  {label or sel}")
            return True
        except Exception:
            continue
    log(f"SKIP {label} (none of {len(selectors)} selectors matched)")
    return False


def wait_for_human(page, predicate, what, poll=2, limit=900):
    """Poll until predicate(page) is true; the human may be acting."""
    log(f"WAITING for: {what} (up to {limit//60} min — take over in the "
        f"window if needed)")
    start = time.time()
    while time.time() - start < limit:
        try:
            if predicate(page):
                return True
        except Exception:
            pass
        time.sleep(poll)
    log(f"TIMEOUT waiting for {what}")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--depart-time", required=True, help="e.g. 20:30")
    ap.add_argument("--expect-price", type=float, default=None)
    args = ap.parse_args()

    prof = load_profile()
    log(f"PAX: {prof['title']} {prof['first_name']} {prof['last_name']} "
        f"({prof.get('name_note', '')})")

    url = (
        "https://www.ryanair.com/gb/en/trip/flights/select"
        f"?adults=1&teens=0&children=0&infants=0&dateOut={args.date}"
        "&isConnectedFlight=false&discount=0&isReturn=false"
        f"&originIata={args.origin}&destinationIata={args.dest}"
        f"&tpAdults=1&tpStartDate={args.date}"
        f"&tpOriginIata={args.origin}&tpDestinationIata={args.dest}"
    )

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=150,
                                     args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(
            locale="en-GB",
            timezone_id="Europe/London",
            viewport={"width": 1380, "height": 900},
        )
        page = ctx.new_page()
        log(f"OPENING {url}")
        page.goto(url, timeout=60000)

        # ---- cookie wall ----------------------------------------------
        try_click(page, [
            'button[data-ref="cookie.accept-all"]',
            'button:has-text("Yes, I agree")',
            'button:has-text("Accept all")',
        ], timeout=8000, label="cookie consent")

        # ---- pick the flight by departure time ------------------------
        time.sleep(3)
        picked = False
        try:
            card = page.locator(
                "flights-flight-card, [data-e2e='flight-card']"
            ).filter(has_text=args.depart_time).first
            card.scroll_into_view_if_needed(timeout=10000)
            # price sanity check before selecting
            if args.expect_price is not None:
                card_text = card.inner_text(timeout=5000)
                import re
                m = re.search(r"€\s*(\d+(?:\.\d{1,2})?)", card_text.replace(",", ""))
                if m:
                    shown = float(m.group(1))
                    delta = shown - args.expect_price
                    log(f"price on card €{shown:.2f} vs expected "
                        f"€{args.expect_price:.2f} (Δ {delta:+.2f})")
                    if delta > 5:
                        log("ABORT-GUARD: fare moved more than €5 above "
                            "expectation. NOT selecting. Review in window.")
                        wait_for_human(page, lambda p: False,
                                       "manual decision (fare moved)", limit=900)
                        return 3
            card.locator(
                "button:has-text('Select'), [data-e2e='flight-card-select']"
            ).first.click(timeout=8000)
            picked = True
            log(f"OK  selected {args.depart_time} flight")
        except Exception as e:
            log(f"MANUAL: couldn't auto-select the {args.depart_time} "
                f"flight ({type(e).__name__}) — click it in the window")

        # ---- fare tier: Basic ------------------------------------------
        time.sleep(2)
        try_click(page, [
            "button:has-text('Basic')",
            "[data-e2e='fare-card--standard'] button",
            "button:has-text('Continue with Basic')",
        ], timeout=6000, label="Basic fare")
        # dismiss 'Regular is better' style upsell modal
        try_click(page, [
            "button:has-text('No, thanks')",
            "[data-ref='enhanced-takeover-beta-desktop__dismiss-cta']",
        ], timeout=4000, label="decline fare upsell")

        # ---- login wall (human does this) ------------------------------
        def past_login(p):
            u = p.url
            return ("passengers" in u or "seats" in u or "extras" in u
                    or "payment" in u)

        if not past_login(page):
            log("MANUAL: if a login/signup wall appears, log into "
                "myRyanair (or continue as guest if offered).")
            if not wait_for_human(page, past_login, "passenger form"):
                log("Leaving browser open for manual completion.")
                wait_for_human(page, lambda p: False, "manual run", limit=3600)
                return 2

        # ---- passenger form --------------------------------------------
        try:
            page.locator("select, [id*='title']").first.select_option(
                label=prof["title"], timeout=6000)
            log("OK  title")
        except Exception:
            try_click(page, [f"button:has-text('{prof['title']}')"],
                      timeout=3000, label="title (custom dropdown)")
        for field, value in (
            ("first", prof["first_name"]),
            ("last", prof["last_name"]),
        ):
            try:
                page.locator(
                    f"input[name*='{field}' i], input[id*='{field}' i]"
                ).first.fill(value, timeout=6000)
                log(f"OK  {field} name = {value}")
            except Exception:
                log(f"MANUAL: type {field} name '{value}' yourself")

        try_click(page, [
            "button:has-text('Continue')",
            "[data-e2e='continue']",
        ], timeout=6000, label="continue past passengers")

        # ---- seats: cheapest option ------------------------------------
        time.sleep(3)
        try_click(page, [
            "button:has-text('Random seat')",
            "[data-e2e='random-seat']",
            "button:has-text('Sit anywhere')",
        ], timeout=8000, label="random (free/cheapest) seat")
        try_click(page, [
            "button:has-text('No, thanks')",
            "button:has-text('Continue')",
        ], timeout=5000, label="decline seat upsell / continue")

        # ---- extras: decline everything --------------------------------
        time.sleep(2)
        for _ in range(3):
            try_click(page, [
                "button:has-text('No, thanks')",
                "button:has-text('Continue')",
                "[data-e2e='checkout-cta']",
            ], timeout=5000, label="skip extras page")
            time.sleep(2)
            if "payment" in page.url:
                break

        # ---- payment page: STOP ----------------------------------------
        if wait_for_human(page, lambda p: "payment" in p.url,
                          "payment page", limit=600):
            log("=" * 60)
            log("PAYMENT PAGE REACHED — I stop here.")
            log(f"  Flight : {args.origin} → {args.dest}  {args.date} "
                f"{args.depart_time}")
            log(f"  PAX    : {prof['title']} {prof['first_name']} "
                f"{prof['last_name']}")
            log(f"  Expect : ~€{args.expect_price}")
            log("  Check the total, enter card, complete 3DS. The window")
            log("  stays open. Forward the confirmation email when done.")
            log("=" * 60)
        else:
            log("Did not reach payment automatically — finish the "
                "remaining step(s) in the window; everything filled so "
                "far is kept.")

        # keep the browser alive for the human
        wait_for_human(page, lambda p: False, "you to finish & close", limit=3600)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

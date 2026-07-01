"""Duffel booking backend — cart-to-payment, human confirms.

v1 strategy: use HOLD orders. Most NDC carriers (TAP, BA, Aer Lingus, etc.)
support 24-72hr holds. Duffel returns a real PNR; the user pays separately
on the airline site or via Duffel's hosted payment widget before the
deadline. This sidesteps card-on-file risk entirely in v1.

When the offer requires instant payment (`payment_requirements.
requires_instant_payment == true`), the dispatcher falls back to printing
the deep-link and asks the user to book manually until v2 wires in
Duffel Payment Intents.

API key: env var DUFFEL_API_KEY. Test keys start with `duffel_test_`.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

import config
from profile import Profile, load as load_profile

BASE_URL = "https://api.duffel.com"
API_VERSION = "v2"
CONFIRM_DIR = config.CONFIRM_DIR


class DuffelError(Exception):
    pass


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.duffel_api_key()}",
        "Duffel-Version": API_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
    }


def _post(path: str, body: dict) -> dict:
    r = requests.post(f"{BASE_URL}{path}", headers=_headers(), json={"data": body}, timeout=30)
    if r.status_code >= 400:
        raise DuffelError(f"{r.status_code} {path}: {r.text[:600]}")
    return r.json()["data"]


def _get(path: str) -> dict:
    r = requests.get(f"{BASE_URL}{path}", headers=_headers(), timeout=30)
    if r.status_code >= 400:
        raise DuffelError(f"{r.status_code} {path}: {r.text[:600]}")
    return r.json()["data"]


# ---- offer search ---------------------------------------------------------


@dataclass
class Slice:
    origin: str
    destination: str
    departure_date: str  # YYYY-MM-DD


def search_offers(slices: list[Slice], adults: int = 1, cabin: str = "economy") -> list[dict]:
    """Run an offer request and return the offers list, cheapest first."""
    body = {
        "slices": [
            {
                "origin": s.origin,
                "destination": s.destination,
                "departure_date": s.departure_date,
            }
            for s in slices
        ],
        "passengers": [{"type": "adult"} for _ in range(adults)],
        "cabin_class": cabin,
    }
    data = _post("/air/offer_requests?return_offers=true", body)
    offers = data.get("offers", [])
    offers.sort(key=lambda o: float(o["total_amount"]))
    return offers


def quote(offer_id: str) -> dict:
    """Re-fetch the offer to check for price movement before booking."""
    from urllib.parse import quote as _urlquote
    return _get(f"/air/offers/{_urlquote(offer_id, safe='')}?return_available_services=true")


# ---- hold order -----------------------------------------------------------


def create_hold(offer: dict, profile: Profile) -> dict:
    """Create a hold order. No payment. Returns PNR + pay-by deadline."""
    reqs = offer.get("payment_requirements", {}) or {}
    if reqs.get("requires_instant_payment"):
        raise DuffelError(
            "This offer requires instant payment. v1 supports holds only. "
            "Use --backend manual to deep-link, or wait for v2 payment-intent path."
        )

    pax_ids = [p["id"] for p in offer["passengers"]]
    body = {
        "type": "hold",
        "selected_offers": [offer["id"]],
        "passengers": profile.to_duffel_passengers(pax_ids),
    }
    order = _post("/air/orders", body)
    _save_confirmation(order)
    return order


def _sanitize_component(value: str) -> str:
    """API-sourced strings become filename components — strip anything that
    could traverse out of CONFIRM_DIR (.. / path separators) or surprise
    the filesystem."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(value)).lstrip(".") or "unknown"


def _save_confirmation(order: dict) -> Path:
    CONFIRM_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIRM_DIR, 0o700)
    pnr = _sanitize_component(order.get("booking_reference", order["id"]))
    when = _sanitize_component(order.get("created_at", "").split("T")[0] or "unknown")
    path = CONFIRM_DIR / f"{when}_{pnr}.json"
    resolved = path.resolve()
    if resolved.parent != CONFIRM_DIR.resolve():
        raise DuffelError(f"refusing confirmation path outside {CONFIRM_DIR}: {resolved}")
    # 0600 from creation (no create-then-chmod window): PNR + passenger PII
    fd = os.open(resolved, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(order, indent=2))
    return path


# ---- CLI entry ------------------------------------------------------------


def _cli():
    import argparse

    ap = argparse.ArgumentParser(description="Duffel booking (sandbox-safe).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="Run offer request, print top offers")
    s.add_argument("origin")
    s.add_argument("destination")
    s.add_argument("date", help="YYYY-MM-DD")
    s.add_argument("--return-date", dest="return_date", default=None)
    s.add_argument("--adults", type=int, default=1)
    s.add_argument("--cabin", default="economy")
    s.add_argument("--top", type=int, default=5)

    q = sub.add_parser("quote", help="Re-fetch an offer by ID")
    q.add_argument("offer_id")

    h = sub.add_parser("hold", help="Create a hold order (no payment)")
    h.add_argument("offer_id")
    h.add_argument("--yes-book", action="store_true",
                   help="Required to actually submit. Without this, prints what would be sent.")

    args = ap.parse_args()

    if args.cmd == "search":
        slices = [Slice(args.origin, args.destination, args.date)]
        if args.return_date:
            slices.append(Slice(args.destination, args.origin, args.return_date))
        offers = search_offers(slices, adults=args.adults, cabin=args.cabin)
        if not offers:
            print("No offers.")
            return
        print(f"{len(offers)} offers, showing top {min(args.top, len(offers))}:\n")
        for o in offers[: args.top]:
            airlines = o["owner"]["name"]
            print(f"  {o['id']}  {o['total_amount']} {o['total_currency']}  {airlines}")

    elif args.cmd == "quote":
        offer = quote(args.offer_id)
        print(f"{offer['id']}  {offer['total_amount']} {offer['total_currency']}  "
              f"expires {offer['expires_at']}")

    elif args.cmd == "hold":
        prof = load_profile()
        offer = quote(args.offer_id)
        airlines = offer["owner"]["name"]
        print("\n--- HOLD CONFIRMATION ---")
        print(f"Offer:      {offer['id']}")
        print(f"Carrier(s): {airlines}")
        print(f"Price:      {offer['total_amount']} {offer['total_currency']}")
        print(f"PAX:        {prof.primary['given_name']} {prof.primary['family_name']}")
        print(f"Expires:    {offer['expires_at']}")
        print("-------------------------\n")
        if not args.yes_book:
            print("Dry-run. Re-run with --yes-book to create the hold.")
            return
        order = create_hold(offer, prof)
        print(f"HELD. PNR: {order.get('booking_reference', order['id'])}")
        print(f"Pay by:    {order.get('payment_status', {}).get('payment_required_by', 'see Duffel dashboard')}")
        print(f"Saved:     {CONFIRM_DIR}/...")


if __name__ == "__main__":
    try:
        _cli()
    except DuffelError as e:
        print(f"duffel error: {e}", file=sys.stderr)
        sys.exit(1)

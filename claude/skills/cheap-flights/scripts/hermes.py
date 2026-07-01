"""hermes — flight booking orchestrator.

Subcommands:
  hermes whoami                       # show config status
  hermes key set <api_key>            # save key to ~/.config/cheap-flights/.env
  hermes profile init                 # interactive passenger profile setup
  hermes profile show                 # print profile (redacted)
  hermes search ORIG DEST DATE        # parallel Duffel + Google search
  hermes book ORIG DEST DATE          # search → pick → hold (interactive)
  hermes quote OFFER_ID               # re-quote a Duffel offer
  hermes hold OFFER_ID                # hold an existing offer (skip search)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import config  # noqa: E402
import book_duffel  # noqa: E402
import profile as profile_mod  # noqa: E402

SEARCH_PY = SCRIPTS_DIR / "search.py"
VENV_PY = SCRIPTS_DIR.parent / ".venv" / "bin" / "python"


# ---- row projection -------------------------------------------------------


@dataclass
class Row:
    source: str          # 'duffel' | 'google'
    airline: str
    price: float
    currency: str
    offer_id: str | None
    bookable: bool
    note: str = ""


def _rows_from_duffel(offers: list[dict]) -> list[Row]:
    rows: list[Row] = []
    for o in offers:
        rows.append(
            Row(
                source="duffel",
                airline=o["owner"]["name"],
                price=float(o["total_amount"]),
                currency=o["total_currency"],
                offer_id=o["id"],
                bookable=not (o.get("payment_requirements") or {}).get("requires_instant_payment", False),
                note="" if not (o.get("payment_requirements") or {}).get("requires_instant_payment") else "instant-pay (v2)",
            )
        )
    return rows


def _rows_from_google(payload: dict) -> list[Row]:
    rows: list[Row] = []
    for f in payload.get("flights", []):
        try:
            price = float(str(f.get("price_value") or "0").replace(",", ""))
        except (TypeError, ValueError):
            price = 0.0
        rows.append(
            Row(
                source="google",
                airline=f.get("name") or f.get("airline") or "?",
                price=price,
                currency=payload.get("currency") or f.get("price_currency") or "EUR",
                offer_id=None,
                bookable=False,
                note="manual",
            )
        )
    return rows


# ---- searches -------------------------------------------------------------


def _duffel_search(orig: str, dest: str, date: str, adults: int) -> list[Row]:
    try:
        offers = book_duffel.search_offers(
            [book_duffel.Slice(orig, dest, date)], adults=adults
        )
        return _rows_from_duffel(offers)
    except Exception as e:  # noqa: BLE001
        print(f"[duffel search failed: {e}]", file=sys.stderr)
        return []


def _google_search(orig: str, dest: str, date: str) -> list[Row]:
    if not SEARCH_PY.exists():
        return []
    py = str(VENV_PY) if VENV_PY.exists() else sys.executable
    try:
        r = subprocess.run(
            [py, str(SEARCH_PY), orig, dest, date, "--json"],
            capture_output=True, text=True, timeout=40,
        )
        if r.returncode != 0:
            return []
        return _rows_from_google(json.loads(r.stdout))
    except Exception as e:  # noqa: BLE001
        print(f"[google search failed: {e}]", file=sys.stderr)
        return []


def parallel_search(orig: str, dest: str, date: str, adults: int = 1) -> list[Row]:
    with ThreadPoolExecutor(max_workers=2) as ex:
        d_fut = ex.submit(_duffel_search, orig, dest, date, adults)
        g_fut = ex.submit(_google_search, orig, dest, date)
        rows = d_fut.result() + g_fut.result()
    rows.sort(key=lambda r: r.price)
    return rows


# ---- rendering ------------------------------------------------------------


def _render_table(rows: list[Row]) -> None:
    if not rows:
        print("No results.")
        return
    mode = config.duffel_mode() if any(r.source == "duffel" for r in rows) else "n/a"
    print(f"\nResults (duffel mode: {mode}, cheapest first)\n")
    print(f"  {'#':>3}  {'src':<6}  {'airline':<20}  {'price':>10}  via")
    print(f"  {'-'*3}  {'-'*6}  {'-'*20}  {'-'*10}  ---")
    for i, r in enumerate(rows, 1):
        via = "hermes" if r.bookable else r.note or "manual"
        price = f"{r.price:.2f} {r.currency}"
        airline = r.airline[:20]
        print(f"  {i:>3}  {r.source:<6}  {airline:<20}  {price:>10}  {via}")
    print()


# ---- interactive picker ---------------------------------------------------


def _pick(rows: list[Row]) -> Row | None:
    bookable_idx = [i for i, r in enumerate(rows, 1) if r.bookable]
    if not bookable_idx:
        print("No hermes-bookable rows. Pick a number to open the deep-link, or q to quit.")
    while True:
        try:
            raw = input("Pick #, or q to quit: ").strip().lower()
        except EOFError:
            return None
        if raw in {"q", "quit", "exit"}:
            return None
        if not raw.isdigit():
            print("Type a number from the list.")
            continue
        n = int(raw)
        if 1 <= n <= len(rows):
            return rows[n - 1]
        print(f"Out of range. 1..{len(rows)}")


def _confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() == "yes book"
    except EOFError:
        return False


# ---- commands -------------------------------------------------------------


def cmd_whoami(_args: argparse.Namespace) -> int:
    info = config.whoami()
    for k, v in info.items():
        print(f"  {k}: {v}")
    return 0


def cmd_key_set(args: argparse.Namespace) -> int:
    key = args.api_key
    if key is None or key == "-":
        # Read the key off stdin instead of argv: argv is visible to any
        # same-UID process via ps and lands in shell history.
        import getpass
        if sys.stdin.isatty():
            key = getpass.getpass("Duffel API key (input hidden): ").strip()
        else:
            key = sys.stdin.readline().strip()
    else:
        print("note: passing the key as an argument exposes it via ps and "
              "shell history — prefer `hermes key set -` and paste it.",
              file=sys.stderr)
    if not key.startswith(("duffel_test_", "duffel_live_")):
        print("Key should start with 'duffel_test_' or 'duffel_live_'.", file=sys.stderr)
        return 2
    path = config.write_env(key)
    print(f"Saved key to {path} (mode 600).")
    print(f"Mode: {config.duffel_mode()}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    rows = parallel_search(args.origin, args.destination, args.date, args.adults)
    _render_table(rows[: args.top])
    return 0 if rows else 1


def cmd_quote(args: argparse.Namespace) -> int:
    offer = book_duffel.quote(args.offer_id)
    print(f"{offer['id']}  {offer['total_amount']} {offer['total_currency']}  "
          f"expires {offer['expires_at']}")
    return 0


def _hold_flow(offer: dict) -> int:
    try:
        prof = profile_mod.load()
    except profile_mod.ProfileError as e:
        print(f"Profile missing: {e}")
        print("Run: hermes profile init")
        return 2
    airline = offer["owner"]["name"]
    price = f"{offer['total_amount']} {offer['total_currency']}"
    name = f"{prof.primary['given_name']} {prof.primary['family_name']}"
    print("\n--- HOLD CONFIRMATION ---")
    print(f"  Offer:    {offer['id']}")
    print(f"  Airline:  {airline}")
    print(f"  Price:    {price}")
    print(f"  PAX:      {name}")
    print(f"  Expires:  {offer['expires_at']}")
    print("-------------------------\n")
    if not _confirm("Type 'yes book' to create the hold: "):
        print("Aborted.")
        return 1
    try:
        order = book_duffel.create_hold(offer, prof)
    except book_duffel.DuffelError as e:
        print(f"Hold failed: {e}", file=sys.stderr)
        return 1
    pnr = order.get("booking_reference") or order["id"]
    pay_by = (order.get("payment_status") or {}).get("payment_required_by")
    print(f"\nHELD. PNR: {pnr}")
    if pay_by:
        print(f"Pay by:    {pay_by}")
    print(f"Saved:     {config.CONFIRM_DIR}/")
    return 0


def cmd_hold(args: argparse.Namespace) -> int:
    offer = book_duffel.quote(args.offer_id)
    return _hold_flow(offer)


def cmd_book(args: argparse.Namespace) -> int:
    rows = parallel_search(args.origin, args.destination, args.date, args.adults)
    if not rows:
        print("No results.")
        return 1
    _render_table(rows[: args.top])
    pick = _pick(rows[: args.top])
    if pick is None:
        return 0
    if pick.source == "google" or not pick.bookable:
        print("\nNot hermes-bookable. Open in browser:")
        print(f"  https://www.skyscanner.net/transport/flights/"
              f"{args.origin.lower()}/{args.destination.lower()}/"
              f"{args.date[8:10]}{args.date[5:7]}{args.date[2:4]}/")
        return 0
    offer = book_duffel.quote(pick.offer_id)
    # Re-quote price-drift guard: abort if delta > €5
    drift = float(offer["total_amount"]) - pick.price
    if abs(drift) > 5.0:
        print(f"Price drift {drift:+.2f} {offer['total_currency']} since search. Aborting.")
        print("Re-run hermes book to re-search.")
        return 1
    return _hold_flow(offer)


# ---- profile wizard -------------------------------------------------------


def _prompt(label: str, default: str | None = None, allow_empty: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            v = input(f"  {label}{suffix}: ").strip()
        except EOFError:
            v = ""
        if not v and default is not None:
            return default
        if v or allow_empty:
            return v
        print("    (required)")


def cmd_profile_init(_args: argparse.Namespace) -> int:
    config.ensure_config_dir()
    existing = {}
    if config.PROFILE_FILE.exists():
        try:
            existing = json.loads(config.PROFILE_FILE.read_text()).get("primary", {})
        except Exception:  # noqa: BLE001
            pass
    print("Passenger profile setup. Names MUST match passport exactly.\n")
    p = {
        "title": _prompt("title (mr/mrs/ms/dr)", existing.get("title") or "mr"),
        "given_name": _prompt("given name", existing.get("given_name")),
        "family_name": _prompt("family name", existing.get("family_name")),
        "born_on": _prompt("born on YYYY-MM-DD", existing.get("born_on")),
        "gender": _prompt("gender (m/f)", existing.get("gender") or "m"),
        "email": _prompt("email", existing.get("email") or "you@example.com"),
        "phone_number": _prompt("phone (+CCxxxx)", existing.get("phone_number")),
    }
    docs = existing.get("identity_documents") or [{}]
    doc = docs[0] if docs else {}
    passport = _prompt("passport number", doc.get("unique_identifier"), allow_empty=True)
    if passport:
        p["identity_documents"] = [{
            "type": "passport",
            "unique_identifier": passport,
            "issuing_country_code": _prompt("issuing country (ISO-2)",
                                            doc.get("issuing_country_code") or "IE"),
            "expires_on": _prompt("passport expires YYYY-MM-DD",
                                  doc.get("expires_on")),
        }]
    p["loyalty_programmes"] = existing.get("loyalty_programmes") or []
    payload = {"primary": p}
    import os as _os
    # 0600 from creation — passport/DOB PII must never be briefly
    # group/world-readable under a default umask
    fd = _os.open(config.PROFILE_FILE, _os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC, 0o600)
    with _os.fdopen(fd, "w") as f:
        f.write(json.dumps(payload, indent=2))
    _os.chmod(config.PROFILE_FILE, 0o600)
    print(f"\nSaved {config.PROFILE_FILE} (mode 600).")
    return 0


def cmd_profile_show(_args: argparse.Namespace) -> int:
    try:
        prof = profile_mod.load()
    except profile_mod.ProfileError as e:
        print(f"{e}")
        return 1
    redacted = dict(prof.raw)
    if "passengers" in redacted:
        redacted["passengers"] = [
            {**p, "identity_documents": "[REDACTED]"} for p in redacted["passengers"]
        ]
    if "primary" in redacted:
        redacted["primary"] = {**redacted["primary"], "identity_documents": "[REDACTED]"}
    print(json.dumps(redacted, indent=2))
    return 0


# ---- entry ----------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="hermes", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("whoami").set_defaults(fn=cmd_whoami)

    ks = sub.add_parser("key").add_subparsers(dest="key_cmd", required=True)
    kset = ks.add_parser("set")
    kset.add_argument("api_key", nargs="?", default=None,
                      help="the key, or '-' (or omit) to read from stdin — "
                           "preferred, keeps the key out of ps/history")
    kset.set_defaults(fn=cmd_key_set)

    pp = sub.add_parser("profile").add_subparsers(dest="profile_cmd", required=True)
    pi = pp.add_parser("init"); pi.set_defaults(fn=cmd_profile_init)
    ps = pp.add_parser("show"); ps.set_defaults(fn=cmd_profile_show)

    s = sub.add_parser("search")
    s.add_argument("origin"); s.add_argument("destination"); s.add_argument("date")
    s.add_argument("--adults", type=int, default=1)
    s.add_argument("--top", type=int, default=10)
    s.set_defaults(fn=cmd_search)

    b = sub.add_parser("book")
    b.add_argument("origin"); b.add_argument("destination"); b.add_argument("date")
    b.add_argument("--adults", type=int, default=1)
    b.add_argument("--top", type=int, default=10)
    b.set_defaults(fn=cmd_book)

    q = sub.add_parser("quote"); q.add_argument("offer_id"); q.set_defaults(fn=cmd_quote)
    h = sub.add_parser("hold"); h.add_argument("offer_id"); h.set_defaults(fn=cmd_hold)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = _build_parser()
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except config.ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    except book_duffel.DuffelError as e:
        print(f"duffel error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

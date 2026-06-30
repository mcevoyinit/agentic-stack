"""Passenger profile loader.

Profile lives at ~/.config/cheap-flights/passenger_profile.json (mode 600).
Never holds card data — payment auth happens in Duffel hosted widget or
the airline's own checkout.
"""
from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

import config

PROFILE_PATH = config.PROFILE_FILE


class ProfileError(Exception):
    pass


@dataclass
class Profile:
    raw: dict

    @property
    def primary(self) -> dict:
        return self.people[0]

    @property
    def people(self) -> list[dict]:
        """All passengers, primary first. Supports legacy 'primary'-only shape."""
        if "passengers" in self.raw and self.raw["passengers"]:
            return self.raw["passengers"]
        if "primary" in self.raw:
            return [self.raw["primary"]] + list(self.raw.get("companions", []))
        return []

    @staticmethod
    def _to_duffel(p: dict, passenger_id: str) -> dict:
        out = {
            "id": passenger_id,
            "title": p["title"],
            "given_name": p["given_name"],
            "family_name": p["family_name"],
            "born_on": p["born_on"],
            "gender": p["gender"],
            "email": p["email"],
            "phone_number": p["phone_number"],
        }
        docs = [
            d for d in p.get("identity_documents", [])
            if d.get("unique_identifier", "").strip()
            and not d["unique_identifier"].startswith("REPLACE")
        ]
        if docs:
            out["identity_documents"] = docs
        return out

    def to_duffel_passenger(self, passenger_id: str) -> dict:
        """Single-PAX convenience (deprecated; prefer to_duffel_passengers)."""
        return self._to_duffel(self.primary, passenger_id)

    def to_duffel_passengers(self, passenger_ids: list[str]) -> list[dict]:
        """Map profile passengers onto Duffel offer passenger IDs by index."""
        people = self.people
        if len(people) < len(passenger_ids):
            raise ProfileError(
                f"Offer needs {len(passenger_ids)} passengers, profile has "
                f"{len(people)}. Add companions via `hermes profile add`."
            )
        return [self._to_duffel(people[i], pid) for i, pid in enumerate(passenger_ids)]

    def loyalty_for(self, carrier_iata: str) -> str | None:
        for lp in self.primary.get("loyalty_programmes", []):
            if lp.get("carrier_iata") == carrier_iata and lp.get("account_number"):
                return lp["account_number"]
        return None


def load(path: Path | None = None) -> Profile:
    p = path or PROFILE_PATH
    if not p.exists():
        raise ProfileError(
            f"No profile at {p}. Copy passenger_profile.example.json there, "
            f"fill it in, and chmod 600."
        )
    # Refuse to read a world-readable profile — it has passport data.
    mode = p.stat().st_mode
    if mode & (stat.S_IRGRP | stat.S_IROTH):
        raise ProfileError(
            f"Profile at {p} is group/world-readable. Run: chmod 600 {p}"
        )
    raw = json.loads(p.read_text())
    _validate(raw)
    return Profile(raw=raw)


def _validate(raw: dict) -> None:
    people = raw.get("passengers")
    if not people:
        if "primary" not in raw:
            raise ProfileError("Profile must have 'passengers' list or 'primary' block")
        people = [raw["primary"]] + list(raw.get("companions", []))
    if not people:
        raise ProfileError("Profile has no passengers")
    required = ["title", "given_name", "family_name", "born_on", "gender", "email", "phone_number"]
    for i, p in enumerate(people):
        missing = [k for k in required if not p.get(k)]
        if missing:
            raise ProfileError(f"Passenger #{i} missing: {missing}")


if __name__ == "__main__":
    # Smoke test: print the loaded profile minus identity docs.
    try:
        prof = load()
    except ProfileError as e:
        print(f"profile error: {e}")
        raise SystemExit(1)
    redacted = dict(prof.raw)
    if "primary" in redacted:
        redacted["primary"] = {**redacted["primary"], "identity_documents": "[REDACTED]"}
    print(json.dumps(redacted, indent=2))

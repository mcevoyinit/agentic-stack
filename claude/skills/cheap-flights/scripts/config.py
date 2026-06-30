"""Config loader for hermes.

API key + mode are read from (in order):
1. Environment variables (DUFFEL_API_KEY, DUFFEL_MODE)
2. ~/.config/cheap-flights/.env (KEY=value lines, mode 600)

The .env file is never committed; the loader refuses to read it if the
file is group/world-readable.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "cheap-flights"
ENV_FILE = CONFIG_DIR / ".env"
PROFILE_FILE = CONFIG_DIR / "passenger_profile.json"
CONFIRM_DIR = CONFIG_DIR / "confirmations"


class ConfigError(Exception):
    pass


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    mode = path.stat().st_mode
    if mode & (stat.S_IRGRP | stat.S_IROTH):
        raise ConfigError(
            f"{path} is group/world-readable. Run: chmod 600 {path}"
        )
    out: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _lookup(key: str, default: str | None = None) -> str | None:
    if key in os.environ and os.environ[key]:
        return os.environ[key]
    return _parse_env_file(ENV_FILE).get(key, default)


def duffel_api_key() -> str:
    k = _lookup("DUFFEL_API_KEY")
    if not k:
        raise ConfigError(
            "No DUFFEL_API_KEY found.\n"
            f"  Either: export DUFFEL_API_KEY=...\n"
            f"  Or:     write it to {ENV_FILE} (mode 600).\n"
            f"  Get a test key at: app.duffel.com → Developers → Access tokens."
        )
    return k


def duffel_mode() -> str:
    """'test' or 'live'. Inferred from the key prefix; explicit DUFFEL_MODE wins."""
    explicit = _lookup("DUFFEL_MODE")
    if explicit:
        return explicit
    k = duffel_api_key()
    return "test" if k.startswith("duffel_test_") else "live"


def ensure_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)
    return CONFIG_DIR


def write_env(api_key: str) -> Path:
    """Save the API key to the .env file with mode 600."""
    ensure_config_dir()
    existing = _parse_env_file(ENV_FILE) if ENV_FILE.exists() else {}
    existing["DUFFEL_API_KEY"] = api_key
    body = "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n"
    ENV_FILE.write_text(body)
    os.chmod(ENV_FILE, 0o600)
    return ENV_FILE


def whoami() -> dict:
    """Return a summary of current config status. Never returns the raw key."""
    out: dict = {
        "config_dir": str(CONFIG_DIR),
        "env_file": str(ENV_FILE),
        "env_file_exists": ENV_FILE.exists(),
        "profile_file": str(PROFILE_FILE),
        "profile_file_exists": PROFILE_FILE.exists(),
        "confirm_dir": str(CONFIRM_DIR),
    }
    try:
        k = duffel_api_key()
        out["duffel_key_set"] = True
        out["duffel_key_preview"] = k[:13] + "..." + k[-4:]
        out["duffel_mode"] = duffel_mode()
    except ConfigError:
        out["duffel_key_set"] = False
    return out

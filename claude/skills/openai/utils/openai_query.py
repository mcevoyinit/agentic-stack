#!/usr/bin/env python3
"""
OpenAI query shim for the AI Council / Kamikaze.

Provides query_openai(prompt, context="") -> dict, matching the interface that
kamikaze/utils/council_query.py imports. Self-contained curl client modelled on
the verified phoenix.py provider (2026-05-29). Keys loaded from
~/.claude/api-keys.env, then project .env.local / .env, then environment.

Model: env OPENAI_MODEL, else a sane default. Override if the frontier moves.
"""

import sys
import os
import json
import subprocess
from pathlib import Path

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.5")  # flagship; probe-verified 2026-06-30. Set OPENAI_MODEL=gpt-5.4 to revert for latency.

SYSTEM = ("You are a frontier reasoning model competing to produce the single "
          "best possible answer. Be rigorous, concrete, and honest about "
          "uncertainty. No filler.")

_loaded = False


def load_env():
    global _loaded
    if _loaded:
        return
    for p in [Path.home() / ".claude" / "api-keys.env",
              Path.cwd() / ".env.local",
              Path.cwd() / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            break
    _loaded = True


def _curl(url, headers, payload, timeout=180):
    cmd = ["curl", "-s", "-S", "--http1.1", "-X", "POST"]
    for h in headers:
        cmd += ["-H", h]
    cmd += ["-d", json.dumps(payload), "--max-time", str(timeout), url]
    last = None
    for _ in range(3):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        except subprocess.TimeoutExpired:
            return None, f"timeout >{timeout}s"
        if r.returncode != 0:
            last = f"curl rc={r.returncode}: {r.stderr[:200]}"
            continue
        try:
            return json.loads(r.stdout), None
        except json.JSONDecodeError:
            last = f"non-JSON: {r.stdout[:200]}"
            if r.stdout.strip():
                break
    return None, last


def query_openai(prompt: str, context: str = "", model: str = None, max_tokens: int = 8192, timeout: int = 280) -> dict:
    load_env()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return {"success": False, "error": "no OPENAI_API_KEY", "response": None}
    model = model or DEFAULT_MODEL
    full = f"{context}\n\n{prompt}" if context else prompt
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": full}],
        "max_completion_tokens": max_tokens,
    }
    data, err = _curl(OPENAI_URL,
                      [f"Authorization: Bearer {key}", "Content-Type: application/json"],
                      payload, timeout=timeout)
    if err:
        return {"success": False, "error": err, "response": None}
    if isinstance(data, dict) and data.get("error"):
        return {"success": False, "error": data["error"].get("message", "api error"), "response": None}
    try:
        return {"success": True, "response": data["choices"][0]["message"]["content"], "raw": data}
    except (KeyError, IndexError, TypeError):
        return {"success": False, "error": f"shape: {json.dumps(data)[:200]}", "response": None}


def main():
    if len(sys.argv) < 2:
        print("Usage: openai_query.py <prompt> [context]", file=sys.stderr)
        sys.exit(1)
    res = query_openai(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
    if res["success"]:
        print(res["response"])
        sys.exit(0)
    print(f"ERROR: {res['error']}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

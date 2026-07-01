#!/usr/bin/env python3
"""
Gemini query shim for the AI Council / Kamikaze.

Provides query_gemini(prompt, context="") -> dict, matching the interface that
kamikaze/utils/council_query.py imports. Self-contained curl client modelled on
the verified phoenix.py provider (2026-05-29), including the thinking-budget
retry: gemini-3.x are thinking models that can spend the whole token budget on
hidden reasoning and return empty text with finishReason MAX_TOKENS; on that we
retry with thinkingBudget=0. Keys from ~/.claude/api-keys.env, then .env.local.

Model: env GEMINI_MODEL, else gemini-3.5-flash (per user default).
"""

import sys
import os
import json
import subprocess
import tempfile
from pathlib import Path

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

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
    # Headers (which include the API key) go to curl via a private 0600
    # temp file (-H @file), never on argv — any same-UID process can read
    # another process's argv through ps/proc for the life of the call.
    fd, hdr_path = tempfile.mkstemp(prefix="gq-hdr-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(headers) + "\n")
        cmd = ["curl", "-s", "-S", "--http1.1", "-X", "POST",
               "-H", f"@{hdr_path}",
               "-d", json.dumps(payload), "--max-time", str(timeout), url]
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
    finally:
        try:
            os.unlink(hdr_path)
        except OSError:
            pass


def _call(url, prompt, max_tokens, no_think, key):
    gen = {"maxOutputTokens": max_tokens}
    if no_think:
        gen["thinkingConfig"] = {"thinkingBudget": 0}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "generationConfig": gen,
    }
    # key travels as a header (via _curl's 0600 header file), not in the
    # URL — URLs land on argv and in any proxy/access log.
    return _curl(url, [f"x-goog-api-key: {key}",
                       "Content-Type: application/json"], payload)


def _text(data):
    try:
        cand = data["candidates"][0]
        parts = cand.get("content", {}).get("parts", []) or []
        return "".join(p.get("text", "") for p in parts), cand.get("finishReason")
    except (KeyError, IndexError, TypeError):
        return "", None


def query_gemini(prompt: str, context: str = "", model: str = None, max_tokens: int = 8192) -> dict:
    load_env()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return {"success": False, "error": "no GEMINI_API_KEY", "response": None}
    model = model or DEFAULT_MODEL
    full = f"{context}\n\n{prompt}" if context else prompt
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    budget = max(max_tokens, 2048)
    data, err = _call(url, full, budget, no_think=False, key=key)
    if err:
        return {"success": False, "error": err, "response": None}
    if isinstance(data, dict) and "error" in data:
        return {"success": False, "error": data["error"].get("message", "api error"), "response": None}
    text, finish = _text(data)
    if not text and finish == "MAX_TOKENS":
        data, err = _call(url, full, budget, no_think=True, key=key)
        if err:
            return {"success": False, "error": err, "response": None}
        if isinstance(data, dict) and "error" in data:
            return {"success": False, "error": data["error"].get("message", "api error"), "response": None}
        text, finish = _text(data)
    if not text:
        return {"success": False, "error": f"empty (finish={finish})", "response": None}
    return {"success": True, "response": text, "raw": data}


def main():
    if len(sys.argv) < 2:
        print("Usage: gemini_query.py <prompt> [context]", file=sys.stderr)
        sys.exit(1)
    res = query_gemini(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
    if res["success"]:
        print(res["response"])
        sys.exit(0)
    print(f"ERROR: {res['error']}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

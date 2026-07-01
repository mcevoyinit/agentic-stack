#!/usr/bin/env python3
"""
Phoenix — Twin-Dragon Dialectic orchestrator.

Two frontier models (the "dragons") chase the same answer. Each round they
cross-feed: every dragon reads the rival's latest answer plus its own, then
must ABSORB the rival's strengths, STRIKE the weaknesses, and TRANSCEND both.
Claude (outside this script) is the crucible that forges the final Phoenix
from the dialectic this script emits.

This file is self-contained: it talks to each provider's HTTP API via curl,
loading keys from ~/.claude/api-keys.env (same convention as the other
skills). No SDKs, no shell aliases, no per-provider helper modules required.

Output: a single JSON object on stdout (the "fire log") — ignition answers,
every interlock round, and convergence signals — for Claude to read and
forge the Phoenix in-context.

Usage:
    python3 phoenix.py --selftest
    python3 phoenix.py --problem-file /path/problem.txt --tier standard \
        --dragons openai,gemini --out /tmp/phoenix.run
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# --------------------------------------------------------------------------
# Key loading (mirrors grok_query.py)
# --------------------------------------------------------------------------

def load_env():
    for p in [Path.home() / ".claude" / "api-keys.env",
              Path.cwd() / ".env.local", Path.cwd() / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            break


def _key(name):
    load_env()
    return os.environ.get(name)


def _hdr_file(headers):
    """Headers (incl. the API key) go to curl via a private 0600 temp file
    (-H @file), never on argv — argv is readable by any same-UID process
    via ps for the life of the call. Caller must unlink the returned path."""
    fd, path = tempfile.mkstemp(prefix="phoenix-hdr-")
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(headers) + "\n")
    return path


def _curl(url, headers, payload, timeout=180):
    # --http1.1: long/large responses can trip HTTP/2 framing errors (rc=16)
    hdr_path = _hdr_file(headers)
    try:
        cmd = ["curl", "-s", "-S", "--http1.1", "-X", "POST",
               "-H", f"@{hdr_path}",
               "-d", json.dumps(payload), "--max-time", str(timeout), url]
        last = None
        for attempt in range(3):  # retry transient curl/network failures
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
                if r.stdout.strip():  # got a body that isn't JSON — don't retry
                    break
        return None, last
    finally:
        try:
            os.unlink(hdr_path)
        except OSError:
            pass


# --------------------------------------------------------------------------
# Providers. Each returns {"success","response","error","model"}.
# Model defaults are the best available at build time (2026-05-29) — edit
# DEFAULT_MODELS as the frontier moves. selftest reports what actually works.
# --------------------------------------------------------------------------

DEFAULT_MODELS = {
    "openai":     "gpt-5.5",            # chat/completions
    "openai_pro": "gpt-5.5-pro",        # Responses API only (reasoning)
    "gemini":     "gemini-3.5-flash",
    "grok":       "grok-4.3",
    "anthropic":  "claude-fable-5",     # needs a valid ANTHROPIC_API_KEY
}

SYSTEM = ("You are a frontier reasoning model competing to produce the single "
          "best possible answer. Be rigorous, concrete, and honest about "
          "uncertainty. No filler.")


def q_openai(prompt, model, max_tokens=4096):
    key = _key("OPENAI_API_KEY")
    if not key:
        return {"success": False, "error": "no OPENAI_API_KEY", "model": model}
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "max_completion_tokens": max_tokens,
    }
    data, err = _curl("https://api.openai.com/v1/chat/completions",
                      [f"Authorization: Bearer {key}", "Content-Type: application/json"],
                      payload)
    if err:
        return {"success": False, "error": err, "model": model}
    if "error" in data:
        return {"success": False, "error": data["error"].get("message", "api error"), "model": model}
    try:
        return {"success": True, "response": data["choices"][0]["message"]["content"], "model": model}
    except (KeyError, IndexError):
        return {"success": False, "error": f"shape: {json.dumps(data)[:200]}", "model": model}


def _gemini_call(url, prompt, max_tokens, no_think, key):
    gen = {"maxOutputTokens": max_tokens}
    if no_think:
        # gemini-3.x are thinking models; thinking can eat the whole token
        # budget and return empty text with finishReason MAX_TOKENS. Disable
        # thinking on retry to guarantee a visible answer.
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


def _gemini_text(data):
    try:
        cand = data["candidates"][0]
        parts = cand.get("content", {}).get("parts", []) or []
        text = "".join(p.get("text", "") for p in parts)
        return text, cand.get("finishReason")
    except (KeyError, IndexError):
        return "", None


def _curl_get(url, headers, timeout=60):
    hdr_path = _hdr_file(headers)
    try:
        cmd = ["curl", "-s", "-S", "--http1.1", "-X", "GET",
               "-H", f"@{hdr_path}",
               "--max-time", str(timeout), url]
        for _ in range(3):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
            except subprocess.TimeoutExpired:
                return None, "get timeout"
            if r.returncode == 0:
                try:
                    return json.loads(r.stdout), None
                except json.JSONDecodeError:
                    return None, f"non-JSON: {r.stdout[:160]}"
        return None, f"curl rc={r.returncode}: {r.stderr[:160]}"
    finally:
        try:
            os.unlink(hdr_path)
        except OSError:
            pass


def _responses_text(data):
    text = data.get("output_text")
    if not text:
        chunks = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        chunks.append(c.get("text", ""))
        text = "".join(chunks)
    return text


def q_openai_responses(prompt, model, max_tokens=4096, poll_secs=8, max_wait=1200,
                       reasoning_effort="medium"):
    """Pro/reasoning models (gpt-5.5-pro) live only on /v1/responses and are slow
    enough that a synchronous call gets the connection dropped (rc=52). Use
    background mode: enqueue, then poll until completed. These models also spend
    output tokens on hidden reasoning, so the budget must cover reasoning + the
    visible answer or the call returns status=incomplete with empty text."""
    key = _key("OPENAI_API_KEY")
    if not key:
        return {"success": False, "error": "no OPENAI_API_KEY", "model": model}
    headers = [f"Authorization: Bearer {key}", "Content-Type: application/json"]
    payload = {
        "model": model, "instructions": SYSTEM, "input": prompt,
        "max_output_tokens": max(max_tokens, 16000),  # reasoning + answer
        "reasoning": {"effort": reasoning_effort},
        "background": True, "store": True,
    }
    data, err = _curl("https://api.openai.com/v1/responses", headers, payload, timeout=90)
    if err:
        return {"success": False, "error": err, "model": model}
    eo = data.get("error")  # Responses API returns "error": null on success
    if eo:
        msg = eo.get("message", "api error") if isinstance(eo, dict) else str(eo)
        return {"success": False, "error": msg, "model": model}
    rid, status = data.get("id"), data.get("status")
    if not rid:
        return {"success": False, "error": f"no id: {json.dumps(data)[:160]}", "model": model}
    waited = 0
    while status in ("queued", "in_progress") and waited < max_wait:
        time.sleep(poll_secs)
        waited += poll_secs
        data, err = _curl_get(f"https://api.openai.com/v1/responses/{rid}", headers)
        if err:
            continue
        status = data.get("status")
    if status not in ("completed", "incomplete"):
        return {"success": False, "error": f"status={status} after {waited}s", "model": model}
    text = _responses_text(data)
    if not text:
        return {"success": False, "error": f"empty (status={status}): {json.dumps(data)[:160]}", "model": model}
    return {"success": True, "response": text, "model": model}


def q_gemini(prompt, model, max_tokens=4096):
    key = _key("GEMINI_API_KEY")
    if not key:
        return {"success": False, "error": "no GEMINI_API_KEY", "model": model}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    # give thinking models headroom; first try keeps thinking on
    budget = max(max_tokens, 2048)
    data, err = _gemini_call(url, prompt, budget, no_think=False, key=key)
    if err:
        return {"success": False, "error": err, "model": model}
    if "error" in data:
        return {"success": False, "error": data["error"].get("message", "api error"), "model": model}
    text, finish = _gemini_text(data)
    if not text and finish == "MAX_TOKENS":
        # thinking ate the budget — retry with thinking disabled
        data, err = _gemini_call(url, prompt, budget, no_think=True, key=key)
        if err:
            return {"success": False, "error": err, "model": model}
        if "error" in data:
            return {"success": False, "error": data["error"].get("message", "api error"), "model": model}
        text, finish = _gemini_text(data)
    if not text:
        return {"success": False, "error": f"empty (finish={finish}): {json.dumps(data)[:160]}", "model": model}
    return {"success": True, "response": text, "model": model}


def q_grok(prompt, model, max_tokens=4096):
    key = _key("GROK_API_KEY")
    if not key:
        return {"success": False, "error": "no GROK_API_KEY", "model": model}
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    data, err = _curl("https://api.x.ai/v1/chat/completions",
                      [f"Authorization: Bearer {key}", "Content-Type: application/json"],
                      payload)
    if err:
        return {"success": False, "error": err, "model": model}
    if "error" in data:
        msg = data["error"] if isinstance(data["error"], str) else data["error"].get("message", "api error")
        return {"success": False, "error": msg, "model": model}
    try:
        return {"success": True, "response": data["choices"][0]["message"]["content"], "model": model}
    except (KeyError, IndexError):
        return {"success": False, "error": f"shape: {json.dumps(data)[:200]}", "model": model}


def q_anthropic(prompt, model, max_tokens=4096):
    key = _key("ANTHROPIC_API_KEY")
    if not key:
        return {"success": False, "error": "no ANTHROPIC_API_KEY", "model": model}
    payload = {
        "model": model, "max_tokens": max_tokens, "system": SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
    }
    data, err = _curl("https://api.anthropic.com/v1/messages",
                      [f"x-api-key: {key}", "anthropic-version: 2023-06-01",
                       "Content-Type: application/json"], payload)
    if err:
        return {"success": False, "error": err, "model": model}
    if data.get("type") == "error":
        return {"success": False, "error": data.get("error", {}).get("message", "api error"), "model": model}
    try:
        text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        return {"success": True, "response": text, "model": model}
    except (KeyError, IndexError):
        return {"success": False, "error": f"shape: {json.dumps(data)[:200]}", "model": model}


PROVIDERS = {"openai": q_openai, "openai_pro": q_openai_responses,
             "gemini": q_gemini, "grok": q_grok, "anthropic": q_anthropic}


def ask(provider, prompt, model=None, max_tokens=4096):
    model = model or DEFAULT_MODELS[provider]
    t0 = time.time()
    out = PROVIDERS[provider](prompt, model, max_tokens)
    out["provider"] = provider
    out["t"] = round(time.time() - t0, 1)
    return out


# --------------------------------------------------------------------------
# Convergence (Jaccard on word sets — lightweight, no deps)
# --------------------------------------------------------------------------

def jaccard(a, b):
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not (sa | sb):
        return 0.0
    return len(sa & sb) / len(sa | sb)


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------

def ignite_prompt(problem):
    return (f"Answer this as rigorously and completely as you can. Give your "
            f"reasoning, then your answer.\n\nPROBLEM:\n{problem}")


def interlock_prompt(problem, rival_ans, own_ans):
    return f"""You and a rival frontier model are both chasing the single best
possible answer to a problem — two dragons spiraling around a flaming pearl.
Each climbs by pushing off the other.

THE PROBLEM:
{problem}

THE RIVAL'S CURRENT ANSWER:
{rival_ans}

YOUR OWN PREVIOUS ANSWER:
{own_ans}

Do three things, in order:
1. ABSORB — name what the rival got right that you missed, and adopt it.
2. STRIKE — name where the rival OR you is wrong, weak, unverified, or
   hand-wavy, and fix it with rigor. Show the correction.
3. TRANSCEND — produce an answer better than BOTH previous answers.

Do not defend your old answer for ego. Keep only what survives scrutiny. If a
claim is uncertain, say so. End with your new, strictly improved answer under
a heading "## NEW ANSWER"."""


# --------------------------------------------------------------------------
# The loop
# --------------------------------------------------------------------------

TIERS = {"quick": 1, "standard": 2, "deep": 3}


def run_phoenix(problem, dragons, tier="standard", converge_at=0.82, max_tokens=4096):
    da, db = dragons
    rounds = TIERS.get(tier, 2)
    log = {"problem": problem, "dragons": dragons, "tier": tier,
           "ignition": {}, "interlock": [], "convergence": None, "notes": []}

    # Phase 0 — ignition (parallel)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as ex:
        fa = ex.submit(ask, da, ignite_prompt(problem), None, max_tokens)
        fb = ex.submit(ask, db, ignite_prompt(problem), None, max_tokens)
        ra, rb = fa.result(), fb.result()
    if not ra["success"] or not rb["success"]:
        log["notes"].append(f"ignition failure: {da}={ra.get('error')} | {db}={rb.get('error')}")
    log["ignition"] = {da: ra, db: rb}
    cur_a = ra.get("response", "") or ""
    cur_b = rb.get("response", "") or ""

    sims = []
    # Phase 1..N — interlock (parallel cross-feed each round)
    for k in range(1, rounds + 1):
        if not cur_a or not cur_b:
            log["notes"].append(f"round {k} skipped: a dragon has no answer")
            break
        pa = interlock_prompt(problem, cur_b, cur_a)
        pb = interlock_prompt(problem, cur_a, cur_b)
        with ThreadPoolExecutor(max_workers=2) as ex:
            fa = ex.submit(ask, da, pa, None, max_tokens)
            fb = ex.submit(ask, db, pb, None, max_tokens)
            na, nb = fa.result(), fb.result()
        if na["success"]:
            cur_a = na["response"]
        if nb["success"]:
            cur_b = nb["response"]
        sim = jaccard(cur_a, cur_b)
        sims.append(sim)
        log["interlock"].append({"round": k, da: na, db: nb, "similarity": round(sim, 3)})
        if sim >= converge_at:
            log["notes"].append(f"converged at round {k} (sim={sim:.2f})")
            break

    log["convergence"] = {
        "similarities": [round(s, 3) for s in sims],
        "final": round(sims[-1], 3) if sims else None,
        "converged": bool(sims and sims[-1] >= converge_at),
    }
    log["final"] = {da: cur_a, db: cur_b}
    return log


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def selftest():
    probe = "Reply with exactly the token PHOENIX_OK and nothing else."
    print("Phoenix provider self-test (best available model each):\n", file=sys.stderr)
    rows = []
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {p: ex.submit(ask, p, probe, None, 64) for p in PROVIDERS}
        for p, f in futs.items():
            r = f.result()
            ok = r.get("success")
            detail = (r.get("response") or r.get("error") or "")[:70].replace("\n", " ")
            rows.append((p, r.get("model"), ok, r.get("t"), detail))
    for p, m, ok, t, d in rows:
        print(f"  {p:10} {m:26} {'OK ' if ok else 'FAIL'} {str(t)+'s':6} {d}", file=sys.stderr)
    working = [p for p, _, ok, _, _ in rows if ok]
    print(f"\nWORKING: {','.join(working) if working else 'NONE'}", file=sys.stderr)
    print(json.dumps({"working": working,
                      "results": [{"provider": p, "model": m, "ok": ok} for p, m, ok, _, _ in rows]}))
    return 0 if len(working) >= 2 else 1


def main():
    ap = argparse.ArgumentParser(description="Phoenix — Twin-Dragon Dialectic")
    ap.add_argument("--problem-file")
    ap.add_argument("--problem")
    ap.add_argument("--tier", default="standard", choices=list(TIERS))
    ap.add_argument("--dragons", default="openai,gemini",
                    help="two providers, e.g. openai,gemini (bench: grok,anthropic)")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--converge-at", type=float, default=0.82)
    ap.add_argument("--out", help="write full JSON fire log to this path too")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--once", help="single-shot one provider (for Claude-in-the-ring runs)")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest())

    if a.once:
        if a.once not in PROVIDERS:
            print(f"ERROR: --once must be one of {list(PROVIDERS)}", file=sys.stderr)
            sys.exit(2)
        prompt = a.problem
        if a.problem_file:
            prompt = Path(a.problem_file).read_text()
        if not prompt:
            print("ERROR: provide --problem or --problem-file", file=sys.stderr)
            sys.exit(2)
        r = ask(a.once, prompt, None, max(a.max_tokens, 8000))
        if a.out:
            Path(a.out).write_text(r.get("response") or ("ERROR: " + str(r.get("error"))))
        if r.get("success"):
            print(r["response"])
            sys.exit(0)
        print("ERROR: " + str(r.get("error")), file=sys.stderr)
        sys.exit(1)

    problem = a.problem
    if a.problem_file:
        problem = Path(a.problem_file).read_text()
    if not problem:
        print("ERROR: provide --problem or --problem-file", file=sys.stderr)
        sys.exit(2)

    dragons = [d.strip() for d in a.dragons.split(",")][:2]
    if len(dragons) != 2 or any(d not in PROVIDERS for d in dragons):
        print(f"ERROR: --dragons must be two of {list(PROVIDERS)}", file=sys.stderr)
        sys.exit(2)

    log = run_phoenix(problem, dragons, a.tier, a.converge_at, a.max_tokens)
    blob = json.dumps(log, indent=2)
    if a.out:
        Path(a.out).write_text(blob)
        print(f"fire log -> {a.out}", file=sys.stderr)
    print(blob)


if __name__ == "__main__":
    main()

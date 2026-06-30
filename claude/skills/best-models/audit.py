#!/usr/bin/env python3
"""
best-models audit engine.

Deterministic half of the /best-models skill. Does the parts that must be
VERIFIED rather than guessed:

  1. Asks each provider's API which model IDs actually exist right now
     (the ground truth — not web hype, not last month's blog post).
  2. Scans ~/.claude/skills for the model IDs the setup currently calls.
  3. Diffs them: which configured IDs are invalid (gone from the API) and
     which have a newer same-family sibling available.
  4. Optionally PINGS a model with a 1-token request to prove it answers
     (listed != works — adversarial verification).

It deliberately does NOT hardcode "X is the best model." Rankings rot. The
script reports what is AVAILABLE and what is CONFIGURED; the skill body
applies judgment with a live web check. Keys load from
~/.claude/api-keys.env (the same convention the other skills use).

Usage:
  audit.py list                       # available models per provider (from API)
  audit.py scan                       # model IDs your skills use + provider map
  audit.py audit            [default] # full diff: stale / invalid / newer-available
  audit.py audit --pretty             # same, human-readable table
  audit.py probe --provider P --model M   # 1-token live ping (proves it answers)

All commands also accept --json to force machine output.
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

SKILLS_DIR = Path.home() / ".claude" / "skills"
KEY_FILES = [Path.home() / ".claude" / "api-keys.env",
             Path.home() / ".claude" / ".env"]

# ---- keys -----------------------------------------------------------------

def load_keys():
    for p in KEY_FILES:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def key(name):
    return os.environ.get(name)

# ---- provider definitions -------------------------------------------------
# Each provider: how to list models, and the regex that recognises one of its
# IDs inside a skill file. The Anthropic chat models you actually run come
# from the Claude Code harness, not this key — so its lineup is reported as
# harness-managed and the API list is best-effort only.

PROVIDERS = {
    "openai": {
        "key": "OPENAI_API_KEY",
        "id_re": re.compile(r"\b(?:gpt-[0-9][0-9.a-z-]*|o[1-9](?:-[a-z]+)?)\b"),
    },
    "xai": {
        "key": "GROK_API_KEY",
        "id_re": re.compile(r"\bgrok-[0-9][0-9.a-z-]*\b"),
    },
    "google": {
        "key": "GEMINI_API_KEY",
        "id_re": re.compile(r"\bgemini-[0-9][0-9.a-z-]*\b"),
    },
    "anthropic": {
        "key": "ANTHROPIC_API_KEY",
        # tight: only real model families, not claude-conversations / claude-mem
        "id_re": re.compile(
            r"\bclaude-(?:opus|sonnet|haiku|fable|instant)[0-9a-z.-]*"
            r"|\bclaude-[0-9][0-9a-z.-]*\b"),
    },
}

# Anthropic chat models the harness exposes (kept current by the fable-5
# rule in claude/rules/; this is a display fallback only, never used to
# rewrite configs).
HARNESS_ANTHROPIC = ["claude-opus-4-8", "claude-fable-5",
                     "claude-sonnet-4-6", "claude-haiku-4-5"]

# ---- http -----------------------------------------------------------------

def _get(url, headers, timeout=25):
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200] if hasattr(e, "read") else ""
        return None, f"HTTP {e.code} {body}"
    except Exception as e:
        return None, str(e)

def _post(url, headers, payload, timeout=40):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300] if hasattr(e, "read") else ""
        return None, f"HTTP {e.code} {body}"
    except Exception as e:
        return None, str(e)

# ---- list available models ------------------------------------------------

def list_models(provider):
    """Return (sorted_ids, error). Sorted newest-version first."""
    k = key(PROVIDERS[provider]["key"])
    if not k:
        return [], "no key"
    if provider == "openai":
        d, err = _get("https://api.openai.com/v1/models",
                      {"Authorization": f"Bearer {k}"})
        if err:
            return [], err
        ids = [m["id"] for m in d.get("data", [])]
    elif provider == "xai":
        d, err = _get("https://api.x.ai/v1/models",
                      {"Authorization": f"Bearer {k}"})
        if err:
            return [], err
        ids = [m["id"] for m in d.get("data", [])]
    elif provider == "google":
        d, err = _get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={k}",
            {})
        if err:
            return [], err
        ids = []
        for m in d.get("models", []):
            mid = m.get("name", "").replace("models/", "")
            methods = m.get("supportedGenerationMethods", [])
            if "generateContent" in methods or not methods:
                ids.append(mid)
    elif provider == "anthropic":
        d, err = _get("https://api.anthropic.com/v1/models",
                      {"x-api-key": k, "anthropic-version": "2023-06-01"})
        if err:
            return [], err
        ids = [m["id"] for m in d.get("data", [])]
    else:
        return [], "unknown provider"
    # keep only this provider's family + sort by version desc
    fam = PROVIDERS[provider]["id_re"]
    ids = [i for i in ids if fam.search(i)]
    ids = sorted(set(ids), key=_version_key, reverse=True)
    return ids, None

_VER_RE = re.compile(r"(\d+(?:\.\d+)*)")

def _version_key(mid):
    """Sort key: (major, minor, ...) tuple parsed from the id, padded."""
    m = _VER_RE.search(mid)
    if not m:
        return (0,)
    parts = tuple(int(x) for x in m.group(1).split("."))
    return parts + (0,) * (4 - len(parts))

def _family(mid):
    """Coarse family stem so gpt-5.5-pro and gpt-5.4 compare as 'gpt' tier.
    Keep the tier suffix (pro/mini/flash/...) so we don't suggest swapping a
    mini for a pro or vice-versa."""
    base = re.sub(r"[-_]?\d.*$", "", mid)        # strip first version onward
    tier = ""
    # order matters: longer/compound tiers before their substrings
    # (non-reasoning before reasoning, flash-lite before flash)
    for t in ("multi-agent", "non-reasoning", "reasoning", "flash-lite",
              "pro", "mini", "nano", "flash", "instant",
              "opus", "sonnet", "haiku", "fable"):
        if t in mid:
            tier = t
            break
    return f"{base}:{tier}"

# ---- scan configured ids --------------------------------------------------

def scan_configs():
    """Return {provider: {model_id: [relative_file, ...]}}."""
    out = {p: {} for p in PROVIDERS}
    if not SKILLS_DIR.exists():
        return out
    for f in SKILLS_DIR.rglob("*"):
        if not f.is_file():
            continue
        # skip the auditor's own files (its docs mention IDs as examples) and
        # any timestamped backups left by a prior swap
        if "best-models" in f.parts or ".bak-" in f.name:
            continue
        if f.suffix.lower() not in (".py", ".md", ".sh", ".json", ".txt", ".js", ".ts"):
            continue
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        for prov, meta in PROVIDERS.items():
            for mid in set(meta["id_re"].findall(text)):
                # findall on alternation can return tuples; normalise
                if isinstance(mid, tuple):
                    mid = next((x for x in mid if x), "")
                mid = mid if isinstance(mid, str) else ""
                m = meta["id_re"].search(mid) if mid else None
                if not mid:
                    continue
                out[prov].setdefault(mid, [])
                rel = str(f.relative_to(SKILLS_DIR))
                if rel not in out[prov][mid]:
                    out[prov][mid].append(rel)
    return out

# ---- diff -----------------------------------------------------------------

def build_audit():
    report = {"providers": {}}
    configured = scan_configs()
    for prov in PROVIDERS:
        avail, err = list_models(prov)
        if prov == "anthropic" and (err or not avail):
            avail = HARNESS_ANTHROPIC
            err = (err + " (showing harness lineup)") if err else None
        conf = configured.get(prov, {})
        # best candidate per family among available
        best_by_fam = {}
        for mid in avail:
            fam = _family(mid)
            if fam not in best_by_fam or _version_key(mid) > _version_key(best_by_fam[fam]):
                best_by_fam[fam] = mid
        findings = []
        for mid, files in sorted(conf.items()):
            valid = mid in avail
            fam = _family(mid)
            newer = best_by_fam.get(fam)
            is_newest = newer == mid or newer is None
            status = "ok"
            suggest = None
            if not valid:
                status = "invalid"      # API no longer lists it
                suggest = newer
            elif not is_newest and _version_key(newer) > _version_key(mid):
                status = "outdated"     # valid but a newer sibling exists
                suggest = newer
            findings.append({
                "id": mid, "files": files, "valid": valid,
                "status": status, "suggest": suggest,
            })
        report["providers"][prov] = {
            "key_present": bool(key(PROVIDERS[prov]["key"])),
            "available_error": err,
            "available_top": avail[:8],
            "best_by_family": best_by_fam,
            "findings": findings,
        }
    return report

# ---- probe ----------------------------------------------------------------

def probe(provider, model):
    k = key(PROVIDERS[provider]["key"])
    if not k:
        return {"ok": False, "error": "no key"}
    if provider == "openai":
        d, err = _post("https://api.openai.com/v1/chat/completions",
                       {"Authorization": f"Bearer {k}",
                        "Content-Type": "application/json"},
                       {"model": model, "max_completion_tokens": 1,
                        "messages": [{"role": "user", "content": "ping"}]})
    elif provider == "xai":
        d, err = _post("https://api.x.ai/v1/chat/completions",
                       {"Authorization": f"Bearer {k}",
                        "Content-Type": "application/json"},
                       {"model": model, "max_tokens": 1,
                        "messages": [{"role": "user", "content": "ping"}]})
    elif provider == "google":
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={k}")
        d, err = _post(url, {"Content-Type": "application/json"},
                       {"contents": [{"parts": [{"text": "ping"}]}],
                        "generationConfig": {"maxOutputTokens": 1}})
    elif provider == "anthropic":
        d, err = _post("https://api.anthropic.com/v1/messages",
                       {"x-api-key": k, "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"},
                       {"model": model, "max_tokens": 1,
                        "messages": [{"role": "user", "content": "ping"}]})
    else:
        return {"ok": False, "error": "unknown provider"}
    # A model that hit our deliberately-tiny token cap DID run — that error
    # proves the id is valid and answering, so treat it as success.
    if err and re.search(r"max_tokens|output limit|max_completion_tokens|"
                         r"finish the message", err, re.I):
        return {"ok": True, "error": None, "note": "answered (hit token cap)"}
    return {"ok": err is None, "error": err}

# ---- rendering ------------------------------------------------------------

def pretty(report):
    lines = []
    sym = {"ok": "OK ", "outdated": "OLD", "invalid": "BAD"}
    for prov, p in report["providers"].items():
        head = f"== {prov.upper()} =="
        if not p["key_present"]:
            lines.append(f"{head}  (no key)")
            continue
        lines.append(head)
        if p["available_error"]:
            one = " ".join(p["available_error"].split())[:90]
            lines.append(f"  api error: {one}")
        top = ", ".join(p["available_top"][:4]) or "(none)"
        lines.append(f"  available: {top}")
        if not p["findings"]:
            lines.append("  configured: (none found)")
        for fnd in p["findings"]:
            s = sym.get(fnd["status"], "?")
            line = f"  [{s}] {fnd['id']}"
            if fnd["suggest"]:
                line += f"  ->  {fnd['suggest']}"
            line += f"   ({len(fnd['files'])} file(s))"
            lines.append(line)
        lines.append("")
    # summary
    stale = sum(1 for p in report["providers"].values()
                for f in p["findings"] if f["status"] != "ok")
    lines.append(f"SUMMARY: {stale} model reference(s) need attention.")
    return "\n".join(lines)

# ---- main -----------------------------------------------------------------

def main():
    load_keys()
    args = sys.argv[1:]
    cmd = args[0] if args and not args[0].startswith("-") else "audit"
    as_json = "--json" in args
    as_pretty = "--pretty" in args

    if cmd == "list":
        out = {}
        for prov in PROVIDERS:
            ids, err = list_models(prov)
            out[prov] = {"error": err, "models": ids}
        if as_pretty and not as_json:
            for prov, v in out.items():
                print(f"== {prov.upper()} ==")
                if v["error"]:
                    print(f"  error: {v['error']}")
                for m in v["models"][:12]:
                    print(f"  {m}")
                print()
        else:
            print(json.dumps(out, indent=2))
        return

    if cmd == "scan":
        conf = scan_configs()
        if as_pretty and not as_json:
            for prov, ids in conf.items():
                print(f"== {prov.upper()} ==")
                for mid, files in sorted(ids.items()):
                    print(f"  {mid}  ({len(files)} file(s))")
                print()
        else:
            print(json.dumps(conf, indent=2))
        return

    if cmd == "probe":
        prov = None
        model = None
        for i, a in enumerate(args):
            if a == "--provider":
                prov = args[i + 1]
            if a == "--model":
                model = args[i + 1]
        if not prov or not model:
            print("usage: audit.py probe --provider P --model M", file=sys.stderr)
            sys.exit(2)
        print(json.dumps(probe(prov, model), indent=2))
        return

    # default: audit
    report = build_audit()
    if as_json or not as_pretty:
        # default to pretty for humans unless --json asked; but always allow json
        if as_json:
            print(json.dumps(report, indent=2))
            return
    print(pretty(report))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""domain availability checker — RDAP first, DNS-over-HTTPS fallback.
Usage:
  check.py <name|domain> [more...]
  bare name   -> checks .com .ai .io .co
  full domain -> checks just that (e.g. labarum.ai)
  --tlds com,ai,io,co,xyz  -> override the default TLD set
Stdlib only, no deps. RDAP is authoritative for .com/.net/.org/.io/.co;
.ai and other ccTLDs use a DNS NS-record fallback (NS present = taken).
"""
import sys, json, urllib.request, urllib.parse, concurrent.futures

DEFAULT_TLDS = ["com", "ai", "io", "co"]

def _get(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "domain-check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None

def rdap(domain):
    code, _ = _get(f"https://rdap.org/domain/{domain}")
    if code == 404:
        return "FREE"
    if code == 200:
        return "taken"
    return None  # RDAP not available for this TLD (e.g. .ai)

def doh_ns(domain):
    code, body = _get(f"https://dns.google/resolve?name={urllib.parse.quote(domain)}&type=NS")
    if not body:
        return "?"
    try:
        d = json.loads(body)
    except Exception:
        return "?"
    if d.get("Status") == 3:          # NXDOMAIN
        return "FREE"
    if d.get("Answer"):               # has nameservers
        return "taken"
    return "maybe"                    # exists in DNS but no NS at this label

def check(domain):
    r = rdap(domain)
    return r if r else doh_ns(domain)

def main():
    argv = sys.argv[1:]
    tlds = DEFAULT_TLDS
    names = []
    i = 0
    while i < len(argv):
        if argv[i] == "--tlds" and i + 1 < len(argv):
            tlds = [t.strip().lstrip(".") for t in argv[i+1].split(",")]
            i += 2
            continue
        names.append(argv[i]); i += 1
    if not names:
        print(__doc__); return

    jobs = []
    for n in names:
        n = n.strip().lower()
        if "." in n:
            jobs.append((n, n))
        else:
            for t in tlds:
                jobs.append((n, f"{n}.{t}"))

    res = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(check, d): d for _, d in jobs}
        for f in concurrent.futures.as_completed(futs):
            res[futs[f]] = f.result()

    sym = {"FREE": "✅ FREE", "taken": "❌ taken", "maybe": "🟡 maybe", "?": "…  ?"}
    cur = None
    for lbl, d in jobs:
        if lbl != cur:
            cur = lbl
            print(f"\n{lbl.upper()}")
        print(f"  {d:<24} {sym.get(res.get(d, '?'), '…  ?')}")
    print()

if __name__ == "__main__":
    main()

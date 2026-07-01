#!/usr/bin/env python3
"""Stop hook: verify every URL in the final assistant message (1) resolves
and (2) actually contains what the link says it contains.

Two checks per URL:
  1. DEAD-LINK: curl it (browser UA, --compressed, follow redirects, short
     timeout). Non-2xx/3xx or no connection -> block.
  2. CONTENT-MISMATCH: take the words used to describe the link (the markdown
     anchor text, else the ~70 chars before a bare URL), keep the salient
     content words, and confirm each appears in the fetched page body. If a
     described word (e.g. "speaker" on a speaker product link) is absent from
     the page, block. EN/ES/PT synonyms are accepted (speaker<->altavoz<->
     coluna) so localized pages don't false-positive.

Loop guard: the same failure set blocks only ONCE per session, so the turn
is never trapped if a link genuinely can't be made to pass (e.g. a host that
hard-blocks automated fetches). When that happens, say so in the reply.
"""
import sys, json, re, hashlib, subprocess, os, tempfile

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
MAX_URLS = 8
TIMEOUT = 8

# words that never count as a described "product/topic" term
STOP = set("""the a an and or of to for in on at is are be this that with from
your you our get got buy now new here link page see check via best top all
both one two only just store official site search results result product
listing listings price prices eur usd com www http https html shop online
order ship shipping deliver delivery address option options route routes""".split())

# generic web/brand tokens we don't force-match (they'd match trivially or
# vary by locale) -- presence not required
GENERIC = set("""amazon mediamarkt fnac worten google apple microsoft store
es pt gb uk us eu home""".split())

# cross-language synonym groups: if a described word is in a group, any member
# present in the page satisfies it
SYNONYMS = [
    {"speaker", "speakers", "altavoz", "altavoces", "coluna", "colunas",
     "lautsprecher", "enceinte"},
    {"phone", "smartphone", "telefono", "telemovel", "telefon"},
    {"laptop", "notebook", "portatil", "portable"},
    {"headphones", "auriculares", "fones", "casque"},
    {"watch", "reloj", "relogio"},
]

def out(obj):
    print(json.dumps(obj)); sys.exit(0)

def strip_tags(html):
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"(?s)<[^>]+>", " ", html)

def keywords(label):
    toks = re.findall(r"[A-Za-zÀ-ÿ]{4,}", label.lower())
    out = []
    for t in toks:
        if t in STOP or t in GENERIC:
            continue
        if t not in out:
            out.append(t)
    # most salient first (longer words tend to be the product noun); cap 4
    out.sort(key=len, reverse=True)
    return out[:4]

def variants(term):
    for g in SYNONYMS:
        if term in g:
            return set(g)
    v = {term}
    if term.endswith("s"):
        v.add(term[:-1])
    else:
        v.add(term + "s")
    return v

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tpath = data.get("transcript_path", "")
    sid = data.get("session_id", "nosession")
    if not tpath or not os.path.exists(tpath):
        sys.exit(0)

    # last assistant text
    text = ""
    try:
        with open(tpath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("type") != "assistant":
                    continue
                msg = e.get("message", {})
                cont = msg.get("content")
                parts = [c.get("text", "") for c in cont
                         if isinstance(c, dict) and c.get("type") == "text"] \
                    if isinstance(cont, list) else []
                if parts:
                    text = "\n".join(parts)
    except Exception:
        sys.exit(0)
    if not text:
        sys.exit(0)

    # collect (url, label) pairs. markdown links first; then bare urls.
    pairs, seen = [], set()
    for m in re.finditer(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", text):
        label, url = m.group(1), m.group(2).rstrip(".,;:!?")
        if url not in seen:
            seen.add(url); pairs.append((url, label))
    for m in re.finditer(r'(?<!\()https?://[^\s)\]}>"\'`]+', text):
        url = m.group(0).rstrip(".,;:!?")
        if url.endswith(")") and "(" not in url:
            url = url[:-1]
        if url in seen:
            continue
        seen.add(url)
        start = max(0, m.start() - 70)
        pairs.append((url, text[start:m.start()]))
    if not pairs:
        sys.exit(0)
    pairs = pairs[:MAX_URLS]

    dead, mism = [], []
    for url, label in pairs:
        try:
            r = subprocess.run(
                ["curl", "-sS", "-A", UA, "--compressed", "-L",
                 "--max-time", str(TIMEOUT),
                 "-w", "\n__HTTP__%{http_code}", url],
                capture_output=True, text=True, timeout=TIMEOUT + 4)
            body, _, code = (r.stdout or "").rpartition("\n__HTTP__")
            code = code.strip()[-3:]
            ok = code.isdigit() and 200 <= int(code) < 400
        except Exception:
            ok, code, body = False, "000", ""
        if not ok:
            dead.append((url, code or "000"))
            continue
        terms = keywords(label)
        if not terms:
            continue
        pagewords = set(re.findall(r"[a-zà-ÿ]+", strip_tags(body).lower()))
        # block only when NONE of the described product words appear (incl.
        # synonyms). Catches a wholly-wrong page; tolerates extra descriptors.
        if not any(variants(t) & pagewords for t in terms):
            mism.append((url, terms))

    if not dead and not mism:
        sys.exit(0)

    sig = hashlib.sha1((sid + "|" +
        "|".join(sorted(u for u, _ in dead)) + "#" +
        "|".join(sorted(u for u, _ in mism))).encode()).hexdigest()
    # per-user temp dir (private on macOS), sid sanitised so a hostile
    # session_id can't point the write elsewhere
    safe_sid = re.sub(r"[^A-Za-z0-9_-]", "_", sid)[:64]
    seenf = os.path.join(tempfile.gettempdir(), f"claude-linkcheck-{safe_sid}.txt")
    prev = set()
    try:
        if os.path.exists(seenf):
            prev = set(open(seenf).read().split())
    except Exception:
        pass
    if sig in prev:
        sys.exit(0)
    try:
        open(seenf, "a").write(sig + "\n")
    except Exception:
        pass

    lines = []
    if dead:
        lines.append("DEAD (did not resolve):")
        lines += [f"  - {u}  (HTTP {c})" for u, c in dead]
    if mism:
        lines.append("CONTENT MISMATCH (page does not mention what you "
                     "called it):")
        lines += [f"  - {u}  (missing: {', '.join(ms)})" for u, ms in mism]
    out({
        "decision": "block",
        "reason": (
            "LINK CHECK FAILED.\n" + "\n".join(lines) +
            "\n\nFor each: open the URL, confirm it shows what you claim, and "
            "fix or remove it. A page missing the product word you used is the "
            "wrong page (e.g. an Amazon search that returns no speaker). If a "
            "host genuinely blocks automated fetches but you have confirmed "
            "the link by other means, say so explicitly in your reply."
        )
    })

if __name__ == "__main__":
    main()

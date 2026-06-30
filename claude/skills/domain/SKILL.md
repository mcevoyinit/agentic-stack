---
name: domain
description: >
  Check domain availability for one or more names across .com/.ai/.io/.co
  (or any TLDs) using authoritative RDAP plus a DNS fallback for ccTLDs
  like .ai. Use when the user wants to know if a name/domain is taken.
  Trigger: "/domain", "domain check", "is <x> taken", "check the domain",
  "is <x>.com free", "are these domains available".
---

# /domain — domain availability checker

When invoked, run the bundled script with whatever names or domains the user
gave:

```bash
python3 ~/.claude/skills/domain/check.py <name1> <name2> ...
# bare name  -> checks .com .ai .io .co
# full domain (has a dot) -> checks just that one
# --tlds com,ai,io,xyz     -> override the TLD set
```

Then present the result as a tight table, FREE ones first, ≤72 chars wide.

## How it decides
- **RDAP** (rdap.org -> the registry) is authoritative for gTLDs
  (.com/.net/.org/.io/.co/...): HTTP 404 = FREE, 200 = taken.
- **.ai and other ccTLDs** have no open RDAP, so it falls back to a
  DNS-over-HTTPS NS lookup (dns.google): nameservers present = taken,
  NXDOMAIN = FREE.

## Honesty rules (important)
- `FREE` from RDAP on a .com is reliable. `FREE`/`maybe` on .ai is a strong
  signal but NOT a registrar guarantee — tell the user to confirm at the
  registrar before relying on it.
- A registered .com that is parked/for-sale still shows `taken` — note that
  it may be acquirable, not dead.
- Availability ≠ clearance. Domain free does not mean trademark-free; for a
  real venture name still run an incumbent + trademark-class check.

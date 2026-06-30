---
name: phoenix
description: "Twin-Dragon Dialectic. The two best frontier models chase the same answer like two dragons spiraling around a flaming pearl — each round eats the other's answer, ABSORBS its strengths, STRIKES its weaknesses, and TRANSCENDS both. Claude is the crucible: it runs the loop, verifies every claim, reads convergence, and forges the Phoenix — a final answer reborn from the dragons' fire and stronger than either.\nUse for the hardest questions where you want a genuine level above any single model: deep strategy, thorny architecture, subtle correctness, high-stakes reasoning.\nTrigger: \"/phoenix\", \"phoenix\", \"twin dragon\", \"two dragons\", \"best of both models\", \"interlock the models\".\n"
last_updated: '2026-05-29'
type: orchestrator
related: [looper, kamikaze, grok, gemini-loop, openai-loop, grok-loop]
---

# Phoenix — Twin-Dragon Dialectic

Two dragons chase one flaming pearl (the truth). They spiral around each
other, each pushing off the other to climb higher. The friction makes fire.
From the fire, the Phoenix rises carrying the pearl.

Concretely: the **two best frontier models available now** answer the same
problem, then repeatedly cross-feed — each model rewrites its answer after
reading the rival's. Claude orchestrates, verifies, and forges the final
answer. This is NOT `looper` (independent, no cross-talk) and NOT `kamikaze`
(3-model council + chairman). Phoenix is **2 models, interlocking, output
cross-fed every round** — fewer minds, deeper coupling, higher ceiling.

The loop runs through a self-contained orchestrator:
`~/.claude/skills/phoenix/phoenix.py`
It hits each provider's HTTP API directly (keys from
`~/.claude/api-keys.env`) — no shell aliases, no CLIs, no per-model helper
scripts. It emits one JSON "fire log" on stdout. Claude reads that and forges
the Phoenix in-context.

---

## The Two Dragons (the 2 best — verified 2026-05-29)

| Slot | Provider / model | Status |
|------|------------------|--------|
| Dragon A | openai `gpt-5.5` | verified OK |
| Dragon B | gemini `gemini-3.5-flash` | verified OK |
| Bench | grok `grok-4.3` | verified OK |

- Defaults live in `DEFAULT_MODELS` at the top of `phoenix.py`. Edit as the
  frontier moves (e.g. `gemini-3.5-pro` when it ships ~June 2026, or a
  `gpt-5.5-pro` slot for the deep tier).
- Gemini 3.x is a thinking model; the client gives it headroom and retries
  with thinking off if reasoning eats the whole token budget (else it
  returns empty with `finishReason: MAX_TOKENS`). Handled — do not "fix".
- `anthropic` is wired as a possible dragon but the stored ANTHROPIC_API_KEY
  is invalid, and Claude is the crucible anyway — leave Claude out of the
  ring by default for cleaner cognitive diversity.
- Any slot is swappable: `--dragons openai,grok` etc. The two just need to
  be the two strongest distinct cognitions for the task.

---

## Effort Tiers (`--tier`)

| Tier | Interlock rounds | Model calls | When |
|------|------------------|-------------|------|
| `quick` | 1 | 4 | fast sharpen |
| `standard` | 2 | 6 | default |
| `deep` | 3 | 8 | hardest |

Ignition is 2 calls (parallel); each interlock round is 2 calls (parallel).
The loop early-stops if the two answers converge (Jaccard ≥ 0.82).

---

## How to Run

1. **Write the problem to a file** (avoids shell-escaping the prompt):
   ```bash
   printf '%s' "FULL PROBLEM TEXT" > /tmp/phoenix_problem.txt
   ```

2. **Run the dialectic** (default tier `standard`, dragons `openai,gemini`):
   ```bash
   python3 ~/.claude/skills/phoenix/phoenix.py \
     --problem-file /tmp/phoenix_problem.txt \
     --tier standard --dragons openai,gemini \
     --out /tmp/phoenix_run.json
   ```
   Stdout (and `--out`) is the JSON fire log:
   `{problem, dragons, tier, ignition, interlock[], convergence, final, notes}`.
   - `ignition` → each dragon's blind first answer.
   - `interlock[]` → per round, each dragon's rewritten answer + `similarity`.
   - `final` → each dragon's last answer.
   - `convergence` → similarity trail + whether they converged.

3. **Forge the Phoenix** (Claude, in-context — the crucible step). Read the
   fire log. Do NOT just paste a dragon's answer or average them. Produce a
   new, superior answer that:
   1. keeps every thread that survived the dragons' fire AND your own check;
   2. resolves remaining disagreements by reasoning to ground truth — for
      code, RUN / type-check it (never return false positives,
      validate outputs); for facts, verify the load-bearing ones;
   3. adds your own frontier judgment where both dragons fell short;
   4. is honest about residual uncertainty (the unresolved crux, if any).
   The Phoenix must be better than either dragon's final answer.

---

## Verification Gate (no false positives)

The dragons are persuasive, not infallible. Two confident models can be
confidently wrong, and Phoenix must not launder that into a settled answer.

- **Code** → actually run / compile / test it. Never ship a dragon's code
  unverified.
- **Facts / numbers** → check the load-bearing ones against a real source.
- **Single-source claims** → if only one dragon asserted it and the other
  never corroborated, mark it unverified.
- **Agreement ≠ proof** → independently sanity-check what both dragons agree
  on; convergence (high similarity) means they stopped diverging, not that
  they are right.
- If something can't be verified, say "I can't verify X" — do not dress it
  as settled.

---

## Output Format (what Claude shows the user)

Lead with the Phoenix (the deliverable). Then a short Fire Log so the user can
audit how it got there. Keep lines ≤72 chars; table for the log.

```
🔥 PHOENIX
<the final, forged answer — the actual deliverable>

— Fire Log —
| Round | Dragon A moved | Dragon B moved |
|-------|----------------|----------------|
| ignite | <one line> | <one line> |
| 1 | <what changed> | <what changed> |
| ... |

Convergence: <converged @ Rk | climbing, capped @ tier | crux unresolved>
Crux (if any): <the one thing they could not settle>
Verified: <what Claude ran/checked; what stayed single-source>
```

A crux they could not settle is a feature, not a bug — it is the sharpest,
highest-value thing the loop found. Surface it plainly.

---

## Preflight

```bash
python3 ~/.claude/skills/phoenix/phoenix.py --selftest
```
Pings every provider with its default model and prints which work. Needs ≥2
working to run. If a default dragon is down, swap `--dragons` to a working
pair (e.g. `openai,grok`) and note the substitution in the Fire Log.

## Notes

- Latency/cost scale with rounds × 2 calls; honor the tier. Both dragons of
  a round run in parallel inside `phoenix.py`.
- Long answers are passed through files / in-process, never inlined into a
  shell arg — no escaping corruption.
- For a Claude-in-the-ring variant, make Claude one dragon (answer
  in-context) and run `phoenix.py` with a single external dragon as the
  other — same loop, Claude both fighting and forging. Default keeps Claude
  purely as crucible.
- Related: `/looper` (independent, no merge), `/kamikaze` (3-model council +
  chairman), `/grok` (single second opinion). Phoenix is the deep 2-model
  interlock.

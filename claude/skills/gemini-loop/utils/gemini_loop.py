#!/usr/bin/env python3
"""
Gemini Loop - Recursive self-deliberation using Gemini 3.5 Flash

Runs 3-4 rounds of Gemini reasoning with different framings:
  R1: Analyst   — deep initial analysis, confident claims
  R2: Adversary — brutal self-critique of R1
  R3: Integrator — battle-tested synthesis of R1 + R2
  R4: Decider   — final structured answer (optional, for high-stakes topics)

Usage:
    python3 gemini_loop.py --topic "Your question here"
    python3 gemini_loop.py --topic "..." --context "background info"
    python3 gemini_loop.py --topic "..." --context-file path/to/doc.md --rounds 4
    python3 gemini_loop.py --topic "..." --output-dir ./output
"""

import sys
import json
import subprocess
import os
import argparse
import tempfile
import time
from pathlib import Path
from datetime import datetime

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"

# Retry config for 503 high-demand / timeouts (new model launch spikes, etc.)
MAX_RETRIES = 8
RETRY_DELAYS = [15, 30, 45, 60, 90, 120, 150, 180]  # seconds between attempts

_api_key = None


def load_env():
    search_paths = [
        Path.home() / '.claude' / 'api-keys.env',
        Path.cwd() / '.env.local',
        Path.cwd() / '.env',
    ]
    for env_path in search_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
            break


def get_api_key():
    global _api_key
    if _api_key is None:
        load_env()
        _api_key = os.environ.get("GEMINI_API_KEY")
        if not _api_key:
            raise ValueError("GEMINI_API_KEY not found in ~/.claude/api-keys.env, .env.local, or environment")
    return _api_key


def _auth_hdr_file(*headers):
    """Auth header goes to curl via a private 0600 temp file (-H @file),
    never on argv — argv is readable by any same-UID process via ps for
    the life of the call. Caller must unlink the returned path."""
    fd, path = tempfile.mkstemp(prefix="hdr-")
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(headers) + "\n")
    return path


def _is_retryable(error_msg: str, returncode: int) -> bool:
    """Return True if this error is worth retrying (503 demand spike, timeout)."""
    if returncode == 28:  # curl timeout
        return True
    retryable_phrases = [
        "high demand", "UNAVAILABLE", "503", "upstream_error",
        "temporarily unavailable", "try again later", "overloaded",
    ]
    return any(p.lower() in error_msg.lower() for p in retryable_phrases)


def call_gemini(prompt: str, round_label: str = "", verbose: bool = True) -> str:
    """Call Gemini API with exponential backoff retry. Returns response text or raises."""
    label = f" [{round_label}]" if round_label else ""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192,
        }
    }

    api_key = get_api_key()
    hdr_path = _auth_hdr_file(f'x-goog-api-key: {api_key}')
    curl_cmd = [
        'curl', '-s', '-S',
        '-H', f'@{hdr_path}',
        '-H', 'Content-Type: application/json',
        '-X', 'POST',
        '-d', json.dumps(payload),
        '--max-time', '180',
        GEMINI_API_URL
    ]

    try:
        last_error = None
        for attempt in range(MAX_RETRIES):
            if verbose:
                attempt_label = f" (attempt {attempt + 1}/{MAX_RETRIES})" if attempt > 0 else ""
                print(f"\n{'='*60}", flush=True)
                print(f"  Calling Gemini{label}{attempt_label}...", flush=True)
                print(f"{'='*60}", flush=True)

            t0 = time.time()
            try:
                result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=185)
            except subprocess.TimeoutExpired:
                last_error = "subprocess timeout"
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    print(f"  ⏳ Timeout. Retrying in {delay}s...", flush=True)
                    time.sleep(delay)
                continue

            elapsed = time.time() - t0
            returncode = result.returncode

            # curl-level failure (timeout = exit 28, network errors, etc.)
            if returncode != 0:
                last_error = f"curl failed (exit {returncode}): {result.stderr.strip()}"
                if _is_retryable(result.stderr, returncode) and attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    print(f"  ⏳ {last_error[:80]}. Retrying in {delay}s...", flush=True)
                    time.sleep(delay)
                    continue
                raise RuntimeError(last_error)

            # Parse JSON
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Invalid JSON: {e}\nResponse: {result.stdout[:300]}")

            # API-level error
            if 'error' in data:
                msg = data['error'].get('message', 'Unknown')
                last_error = f"API error: {msg}"
                if _is_retryable(msg, 0) and attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    print(f"  ⏳ {last_error[:100]}. Retrying in {delay}s...", flush=True)
                    time.sleep(delay)
                    continue
                raise RuntimeError(last_error)

            # Empty candidates
            if 'candidates' not in data or not data['candidates']:
                raise RuntimeError(f"No candidates in response: {result.stdout[:300]}")

            # Success
            candidate = data['candidates'][0]
            parts = candidate.get('content', {}).get('parts', [])
            text = parts[0].get('text', '') if parts else ''

            if verbose:
                tokens = data.get('usageMetadata', {})
                print(f"  ✓ Done in {elapsed:.1f}s | in={tokens.get('promptTokenCount','?')} out={tokens.get('candidatesTokenCount','?')} tokens", flush=True)

            return text

        raise RuntimeError(f"Exhausted {MAX_RETRIES} retries. Last error: {last_error}")
    finally:
        try:
            os.unlink(hdr_path)
        except OSError:
            pass


# ─── Round Prompts ────────────────────────────────────────────────────────────

def r1_analyst_prompt(topic: str, context: str) -> str:
    ctx_block = f"\n\nCONTEXT:\n{context}" if context else ""
    return f"""You are a world-class analyst producing the definitive analysis of a topic.

Rules:
- Make real, confident claims. Do not hedge everything.
- Use headers and structure — this output will be passed to other reasoning agents.
- Show your reasoning, not just your conclusions.
- Assign confidence levels (HIGH / MEDIUM / LOW) to your key claims.
- Say what most analysts miss or get wrong about this.{ctx_block}

TOPIC TO ANALYZE:
{topic}

Produce your analysis with these sections:
1. **Core Thesis** — What is actually true here? (2-3 sentences, no hedging)
2. **Key Insights** — 5-7 numbered insights ranked by importance, each with confidence level
3. **Hidden Dynamics** — What do most people miss or misunderstand?
4. **Key Tensions** — Where is there genuine uncertainty or tradeoff?
5. **Weak Points in This Analysis** — Where could you be wrong?

Be exhaustive. This is Round 1 of a multi-round deliberation."""


def r2_adversary_prompt(topic: str, r1: str) -> str:
    return f"""You are a ruthless intellectual adversary. Your only job is to find what is WRONG with the analysis below.

You are not trying to be balanced. You are trying to break it.

Attack vectors you must attempt:
- What assumptions are smuggled in and never justified?
- Which "HIGH confidence" claims are actually fragile?
- What evidence would completely overturn this analysis?
- What's missing that would fundamentally change the conclusion?
- What are the 3 most likely failure modes of this reasoning?
- Are there alternative framings that produce completely different answers?
- What is the steelman of the OPPOSITE view?

ORIGINAL TOPIC: {topic}

ANALYSIS TO ATTACK:
{r1}

Produce:
1. **Fatal Flaws** — Claims that are simply wrong or unjustified (be specific, cite the claim)
2. **Ommissions** — What critically important factors were not considered?
3. **Alternative Frame** — If you start from the opposite assumption, where does it lead?
4. **Steelman Opposition** — The best possible case against this analysis
5. **Surviving Claims** — What from the original analysis actually holds up under attack?

Do not soften. The goal is truth, not comfort."""


def r3_integrator_prompt(topic: str, r1: str, r2: str) -> str:
    return f"""You have seen a rigorous analysis and a brutal adversarial critique of that analysis.

Your job is to produce the battle-tested, integrated version — the version that survives scrutiny.

Rules:
- What the adversary killed: drop it
- What survived: keep it, but note it survived attack
- What the adversary missed: note what the original analysis got right that the adversary failed to dent
- What new insight emerged from the tension between analysis and critique: highlight this prominently
- Resolve contradictions — don't leave them hanging with "on the other hand"

ORIGINAL TOPIC: {topic}

ROUND 1 — ANALYSIS:
{r1}

ROUND 2 — ADVERSARIAL CRITIQUE:
{r2}

Produce the synthesis with:
1. **What Survives** — Claims that held up under adversarial attack (with why)
2. **What Was Rightfully Killed** — Claims that didn't survive (with why)
3. **New Emergent Insights** — What became clearer through the conflict?
4. **The Integrated View** — The corrected, strengthened thesis
5. **Remaining Genuine Uncertainty** — What is still actually unresolved?

This is the truth that emerges from deliberation. Make it count."""


def r4_decider_prompt(topic: str, r3: str) -> str:
    return f"""You have seen a full deliberation process — analysis, adversarial critique, and integration.

Now produce the final structured answer. This is what gets acted on.

ORIGINAL TOPIC: {topic}

DELIBERATION SYNTHESIS:
{r3}

Output EXACTLY this format:

## Executive Summary
[3 sentences maximum. What is the answer? No hedging.]

## Top 5 Findings
[Numbered, ranked by importance. One sentence each. Actionable and specific.]

## Recommended Actions
[Concrete, specific actions. "Do X by Y" format. If not applicable, say what to investigate first.]

## What Remains Uncertain
[Maximum 3 items. Only genuine uncertainty — things that would actually change the answer if resolved.]

## Confidence Assessment
Overall confidence in this analysis: [0-100]%
Reasoning: [One sentence on why this confidence level]

Be definitive. Someone is going to act on this."""


# ─── Main Loop ────────────────────────────────────────────────────────────────

def run_loop(topic: str, context: str = "", rounds: int = 3, output_dir: str = None) -> dict:
    """
    Run the Gemini deliberation loop.

    Returns dict with all round outputs.
    """
    print(f"\n{'#'*60}", flush=True)
    print(f"  GEMINI LOOP — {rounds} rounds", flush=True)
    print(f"  Topic: {topic[:80]}{'...' if len(topic) > 80 else ''}", flush=True)
    print(f"{'#'*60}", flush=True)

    results = {"topic": topic, "context": context, "rounds": {}}

    # Round 1: Analyst
    print(f"\n[R1] ANALYST — Building initial analysis...", flush=True)
    r1 = call_gemini(r1_analyst_prompt(topic, context), "R1 Analyst")
    results["rounds"]["r1_analyst"] = r1
    print(r1, flush=True)

    # Round 2: Adversary
    print(f"\n[R2] ADVERSARY — Attacking Round 1...", flush=True)
    r2 = call_gemini(r2_adversary_prompt(topic, r1), "R2 Adversary")
    results["rounds"]["r2_adversary"] = r2
    print(r2, flush=True)

    # Round 3: Integrator
    print(f"\n[R3] INTEGRATOR — Synthesizing R1 + R2...", flush=True)
    r3 = call_gemini(r3_integrator_prompt(topic, r1, r2), "R3 Integrator")
    results["rounds"]["r3_integrator"] = r3
    print(r3, flush=True)

    # Round 4: Decider (optional)
    if rounds >= 4:
        print(f"\n[R4] DECIDER — Final structured answer...", flush=True)
        r4 = call_gemini(r4_decider_prompt(topic, r3), "R4 Decider")
        results["rounds"]["r4_decider"] = r4
        print(r4, flush=True)
    else:
        r4 = None

    # Build final report
    final = r4 if r4 else r3
    results["final"] = final

    # Save outputs if requested
    if output_dir:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = Path(output_dir) / f"gemini_loop_{ts}"
        out_path.mkdir(parents=True, exist_ok=True)

        # Save each round
        round_labels = [("r1_analyst", "R1_ANALYST"), ("r2_adversary", "R2_ADVERSARY"),
                        ("r3_integrator", "R3_INTEGRATOR")]
        if r4:
            round_labels.append(("r4_decider", "R4_DECIDER"))

        for key, label in round_labels:
            if key in results["rounds"]:
                (out_path / f"{label}.md").write_text(results["rounds"][key])

        # Save final report
        report = f"""# Gemini Loop Report
**Topic**: {topic}
**Rounds**: {rounds}
**Date**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## Round 1: Analyst
{results["rounds"]["r1_analyst"]}

---

## Round 2: Adversary
{results["rounds"]["r2_adversary"]}

---

## Round 3: Integrator
{results["rounds"]["r3_integrator"]}
"""
        if r4:
            report += f"\n---\n\n## Round 4: Final Decision\n{r4}\n"

        (out_path / "FINAL_REPORT.md").write_text(report)
        print(f"\n\nOutputs saved to: {out_path}", flush=True)
        results["output_dir"] = str(out_path)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Loop — Recursive self-deliberation for maximum insight",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 gemini_loop.py --topic "Should we build our own auth vs use Auth0?"
  python3 gemini_loop.py --topic "Analyze platform pivot strategy" --context "We build developer tools" --rounds 4
  python3 gemini_loop.py --topic "..." --context-file context.md --output-dir ./docs/analysis
        """
    )
    parser.add_argument('--topic', required=True, help='The question or topic to analyze')
    parser.add_argument('--context', default='', help='Optional context string')
    parser.add_argument('--context-file', help='Optional file to read context from')
    parser.add_argument('--rounds', type=int, default=3, choices=[3, 4],
                        help='3 rounds (default) or 4 for final Decision round')
    parser.add_argument('--output-dir', help='Directory to save outputs (optional)')

    args = parser.parse_args()

    context = args.context
    if args.context_file:
        ctx_path = Path(args.context_file)
        if not ctx_path.exists():
            print(f"ERROR: context-file not found: {args.context_file}", file=sys.stderr)
            sys.exit(1)
        file_context = ctx_path.read_text()
        context = f"{context}\n\n{file_context}".strip() if context else file_context

    try:
        results = run_loop(
            topic=args.topic,
            context=context,
            rounds=args.rounds,
            output_dir=args.output_dir
        )

        print(f"\n\n{'#'*60}", flush=True)
        print("  GEMINI LOOP COMPLETE", flush=True)
        print(f"{'#'*60}\n", flush=True)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

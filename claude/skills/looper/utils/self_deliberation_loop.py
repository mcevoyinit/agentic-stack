#!/usr/bin/env python3
"""
Generic 4-round self-deliberation loop for any OpenAI-compatible API.

Rounds:
  R1 ANALYST    — Bold thesis with confidence ratings
  R2 ADVERSARY  — Ruthless attack on R1's thesis
  R3 INTEGRATOR — Synthesize what survived, surface emergent insights
  R4 DECIDER    — Final recommendation with specific actions

Each round feeds the output of all prior rounds as context.
"""

import sys
import json
import subprocess
import os
import tempfile
import time
import argparse
from pathlib import Path
from datetime import datetime


def load_env():
    """Load API keys from standard locations."""
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


ROUND_PROMPTS = {
    1: """You are the ANALYST. Your job is to make the STRONGEST possible case for your recommended strategy.

INSTRUCTIONS:
- State your recommended strategy clearly upfront
- List 5 numbered Key Insights with confidence ratings (HIGH/MEDIUM/LOW)
- Include a "Hidden Dynamics" section — what do most analysts miss?
- Identify Key Tensions in the decision
- Self-identify your 2-3 weakest assumptions
- Be SPECIFIC: include exact numbers, dates, price levels, and amounts
- Do NOT hedge. Take a strong position.""",

    2: """You are the ADVERSARY. Your job is to RUTHLESSLY ATTACK the Analyst's thesis from Round 1.

INSTRUCTIONS:
- Lead with "The Analyst's thesis is dangerously flawed because..."
- Name specific "Fatal Flaws" — pseudo-mathematics, structural inversions, confirmation bias
- Attack every HIGH confidence claim — find the weakest link
- "Omissions" section: what did the Analyst conveniently ignore?
- Propose an "Alternative Frame" — the inverted thesis
- Steelman the opposition (strongest case AGAINST the Analyst)
- "Surviving Claims" — grudgingly admit what actually holds up (max 2)
- Be brutal. Your job is to BREAK the thesis, not validate it.""",

    3: """You are the INTEGRATOR. Your job is to SYNTHESIZE the Analyst and Adversary into a corrected view.

INSTRUCTIONS:
- "What Survives" — bedrock reality that both rounds agree on
- "What Was Rightfully Killed" — flawed claims the Adversary correctly exposed
- "What the Adversary Missed" — blind spots in R2's attack
- **NEW EMERGENT INSIGHT** — a synthesis that NEITHER R1 nor R2 fully captured (this is your most important contribution)
- "The Integrated View" — corrected thesis with phase-by-phase breakdown
- "Remaining Genuine Uncertainty" — honest open questions that can't be resolved from available data
- Include specific numbers: how many tokens, at what price, by what date""",

    4: """You are the DECIDER. Your job is to deliver a FINAL, ACTIONABLE recommendation.

INSTRUCTIONS:
- Executive Summary (2 sentences max)
- Top 5 Findings (ranked by impact, with confidence %)
- **RECOMMENDED ACTION** — specific, dated, with exact amounts:
  - What to do this week
  - What to do by end of April
  - What to do by end of June
  - What to do by August 31 (deadline)
  - Price triggers that change the plan (stop-losses, take-profits)
- Risk Matrix: what breaks this plan? (2-3 scenarios with mitigations)
- Confidence Assessment with reasoning
- One sentence: "If I'm wrong, the most likely way I'm wrong is..."
"""
}


def call_api(api_url, api_key, model, messages, max_tokens=4096, temperature=0.7, timeout=180):
    """Call an OpenAI-compatible chat API via curl."""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    # Auth header goes to curl via a private 0600 temp file (-H @file),
    # never on argv — argv is readable by any same-UID process via ps
    # for the life of the call.
    fd, hdr_path = tempfile.mkstemp(prefix="hdr-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(f'Authorization: Bearer {api_key}\n')
        curl_cmd = [
            'curl', '-s', '-S',
            '-H', f'@{hdr_path}',
            '-H', 'Content-Type: application/json',
            '-X', 'POST',
            '-d', json.dumps(payload),
            '--max-time', str(timeout),
            api_url,
        ]

        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=timeout + 10)

        if result.returncode != 0:
            raise RuntimeError(f'curl failed: {result.stderr[:200]}')

        data = json.loads(result.stdout)

        if 'error' in data:
            raise RuntimeError(f"API error: {data['error'].get('message', str(data['error']))}")

        if 'choices' in data and data['choices']:
            return data['choices'][0]['message']['content']

        raise RuntimeError(f'Unexpected response: {result.stdout[:300]}')
    finally:
        try:
            os.unlink(hdr_path)
        except OSError:
            pass


def run_loop(api_url, api_key, model, model_label, topic, context, rounds, output_dir):
    """Run the full self-deliberation loop."""
    round_outputs = {}
    all_output = []

    header = f"""
###############################################################
  {model_label} LOOP — {rounds} rounds
###############################################################
"""
    print(header, flush=True)
    all_output.append(header)

    for r in range(1, rounds + 1):
        round_names = {1: "ANALYST", 2: "ADVERSARY", 3: "INTEGRATOR", 4: "DECIDER"}
        round_name = round_names[r]

        print(f"\n[R{r}] {round_name}", flush=True)
        print(f"{'=' * 60}", flush=True)
        t0 = time.time()

        # Build messages
        system_msg = ROUND_PROMPTS[r]
        user_content = f"TOPIC: {topic}\n\n"
        if context:
            user_content += f"CONTEXT:\n{context}\n\n"

        # Feed prior rounds
        for prev_r in range(1, r):
            prev_name = round_names[prev_r]
            user_content += f"\n--- ROUND {prev_r} ({prev_name}) OUTPUT ---\n{round_outputs[prev_r]}\n"

        if r == 1:
            user_content += "\nDeliver your analysis now."
        elif r == 2:
            user_content += "\nAttack the Analyst's thesis now. Be ruthless."
        elif r == 3:
            user_content += "\nSynthesize Rounds 1 and 2 now. Surface your emergent insight."
        elif r == 4:
            user_content += "\nDeliver your final decision now. Be specific and actionable."

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_content},
        ]

        try:
            response = call_api(api_url, api_key, model, messages,
                                max_tokens=4096, temperature=0.7 if r != 4 else 0.5)
            elapsed = time.time() - t0
            round_outputs[r] = response

            output_block = f"\n[R{r}] {round_name}\n{'=' * 60}\n{response}\n\nDone in {elapsed:.1f}s\n"
            print(output_block, flush=True)
            all_output.append(output_block)

        except Exception as e:
            elapsed = time.time() - t0
            error_msg = f"\n[R{r}] {round_name} — FAILED ({elapsed:.1f}s): {e}\n"
            print(error_msg, flush=True)
            all_output.append(error_msg)
            round_outputs[r] = f"[FAILED: {e}]"

    # Save to output dir if specified
    full_text = '\n'.join(all_output)
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = Path(output_dir) / f"FINAL_REPORT.md"
        report = f"# {model_label} Self-Deliberation\n**Topic**: {topic}\n**Rounds**: {rounds}\n**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{full_text}"
        out_path.write_text(report)

    return full_text


# --- Model configurations ---

MODELS = {
    'gemini': {
        'url': 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
        'key_env': 'GEMINI_API_KEY',
        'model': 'gemini-3.5-flash',
        'label': 'Gemini 3.5 Flash',
    },
    'openai': {
        'url': 'https://api.openai.com/v1/chat/completions',
        'key_env': 'OPENAI_API_KEY',
        'model': 'gpt-5.5',
        'label': 'GPT-4.1',
    },
    'grok': {
        'url': 'https://api.x.ai/v1/chat/completions',
        'key_env': 'GROK_API_KEY',
        'model': 'grok-4.3',
        'label': 'Grok 4.20',
    },
}


def main():
    parser = argparse.ArgumentParser(description="Self-deliberation loop for a single model")
    parser.add_argument('--model', required=True, choices=list(MODELS.keys()))
    parser.add_argument('--topic', required=True)
    parser.add_argument('--context', default='')
    parser.add_argument('--context-file', help='File to read context from')
    parser.add_argument('--rounds', type=int, default=4, choices=[3, 4])
    parser.add_argument('--output-dir', help='Directory to save outputs')
    args = parser.parse_args()

    load_env()

    cfg = MODELS[args.model]
    api_key = os.environ.get(cfg['key_env'])
    if not api_key:
        print(f"ERROR: {cfg['key_env']} not found", file=sys.stderr)
        sys.exit(1)

    context = args.context
    if args.context_file:
        context = Path(args.context_file).read_text()

    run_loop(cfg['url'], api_key, cfg['model'], cfg['label'],
             args.topic, context, args.rounds, args.output_dir)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Looper - Run all three self-deliberation loops in parallel.

Fires gemini-loop, openai-loop, and grok-loop concurrently.
Each model argues with itself independently (no cross-model synthesis).

Usage:
    python3 looper.py --topic "Your question here"
    python3 looper.py --topic "..." --models gemini,grok --rounds 4
    python3 looper.py --topic "..." --context-file docs/arch.md --output-dir docs/analysis
"""

import sys
import os
import argparse
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

SKILLS_DIR = Path.home() / '.claude' / 'skills'

LOOP_SCRIPTS = {
    'gemini': SKILLS_DIR / 'gemini-loop' / 'utils' / 'gemini_loop.py',
    'openai': SKILLS_DIR / 'openai-loop' / 'utils' / 'openai_loop.py',
    'grok':   SKILLS_DIR / 'grok-loop'   / 'utils' / 'grok_loop.py',
}

MODEL_LABELS = {
    'gemini': 'Gemini 3.5 Flash',
    'openai': 'GPT-4.1',
    'grok':   'Grok 4.20',
}


def run_single_loop(model: str, topic: str, context: str, context_file: str,
                    rounds: int, output_dir: str) -> dict:
    """Run a single model's loop script as a subprocess. Returns result dict."""
    script = LOOP_SCRIPTS[model]
    if not script.exists():
        return {
            'model': model,
            'success': False,
            'error': f'Script not found: {script}',
            'output': '',
            'elapsed': 0,
        }

    cmd = ['python3', str(script), '--topic', topic, '--rounds', str(rounds)]

    if context:
        cmd.extend(['--context', context])
    if context_file:
        cmd.extend(['--context-file', context_file])
    if output_dir:
        model_out = str(Path(output_dir) / model)
        cmd.extend(['--output-dir', model_out])

    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,  # 15 min max per loop
        )
        elapsed = time.time() - t0

        return {
            'model': model,
            'success': result.returncode == 0,
            'error': result.stderr.strip() if result.returncode != 0 else '',
            'output': result.stdout,
            'elapsed': elapsed,
        }
    except subprocess.TimeoutExpired:
        return {
            'model': model,
            'success': False,
            'error': 'Timeout (>15 min)',
            'output': '',
            'elapsed': time.time() - t0,
        }
    except Exception as e:
        return {
            'model': model,
            'success': False,
            'error': str(e),
            'output': '',
            'elapsed': time.time() - t0,
        }


def extract_final_round(output: str, rounds: int) -> str:
    """Extract the final round output from a loop's stdout."""
    # Look for R4 or R3 section markers
    target = '[R4] DECIDER' if rounds >= 4 else '[R3] INTEGRATOR'
    idx = output.rfind(target)
    if idx >= 0:
        # Get everything after the marker line
        lines = output[idx:].split('\n')
        # Skip the header lines (marker + separator)
        content_start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('Calling ') or line.strip().startswith('Done in '):
                continue
            if '=' * 20 in line:
                continue
            if line.strip() == target.strip():
                continue
            content_start = i
            break
        return '\n'.join(lines[content_start:]).strip()
    return output[-3000:]  # Fallback: last 3000 chars


def main():
    parser = argparse.ArgumentParser(
        description="Looper - Parallel self-deliberation across all models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 looper.py --topic "Should we build our own auth vs use Auth0?"
  python3 looper.py --topic "..." --models gemini,grok --rounds 4
  python3 looper.py --topic "..." --context-file docs/arch.md --output-dir docs/analysis
        """
    )
    parser.add_argument('--topic', required=True, help='The question or topic to analyze')
    parser.add_argument('--context', default='', help='Optional context string')
    parser.add_argument('--context-file', help='Optional file to read context from')
    parser.add_argument('--rounds', type=int, default=3, choices=[3, 4],
                        help='3 rounds (default) or 4 for final Decision round')
    parser.add_argument('--models', default='all',
                        help='Comma-separated: gemini,openai,grok or "all" (default)')
    parser.add_argument('--output-dir', help='Directory to save outputs (optional)')

    args = parser.parse_args()

    # Parse model selection
    if args.models == 'all':
        models = list(LOOP_SCRIPTS.keys())
    else:
        models = [m.strip().lower() for m in args.models.split(',')]
        invalid = [m for m in models if m not in LOOP_SCRIPTS]
        if invalid:
            print(f"ERROR: Unknown models: {invalid}. Valid: {list(LOOP_SCRIPTS.keys())}", file=sys.stderr)
            sys.exit(1)

    print(f"\n{'#'*60}", flush=True)
    print(f"  LOOPER - Parallel Self-Deliberation", flush=True)
    print(f"  Models: {', '.join(MODEL_LABELS[m] for m in models)}", flush=True)
    print(f"  Rounds: {args.rounds}", flush=True)
    print(f"  Topic: {args.topic[:70]}{'...' if len(args.topic) > 70 else ''}", flush=True)
    print(f"{'#'*60}\n", flush=True)

    # Create output dir if needed
    if args.output_dir:
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Launch all loops in parallel
    t0 = time.time()
    results = {}

    with ThreadPoolExecutor(max_workers=len(models)) as executor:
        futures = {
            executor.submit(
                run_single_loop, model, args.topic, args.context,
                args.context_file, args.rounds, args.output_dir
            ): model
            for model in models
        }

        for future in as_completed(futures):
            model = futures[future]
            try:
                result = future.result()
                results[model] = result
                status = 'OK' if result['success'] else 'FAILED'
                print(f"\n  [{MODEL_LABELS[model]}] {status} ({result['elapsed']:.1f}s)", flush=True)
                if not result['success']:
                    print(f"    Error: {result['error'][:200]}", flush=True)
            except Exception as e:
                results[model] = {
                    'model': model, 'success': False,
                    'error': str(e), 'output': '', 'elapsed': 0,
                }
                print(f"\n  [{MODEL_LABELS[model]}] EXCEPTION: {e}", flush=True)

    total_elapsed = time.time() - t0

    # Print summary
    print(f"\n\n{'#'*60}", flush=True)
    print(f"  LOOPER COMPLETE - {total_elapsed:.1f}s wall-clock", flush=True)
    print(f"{'#'*60}\n", flush=True)

    for model in models:
        r = results.get(model, {})
        label = MODEL_LABELS[model]
        print(f"\n{'='*60}", flush=True)
        print(f"  {label} — Final Synthesis", flush=True)
        print(f"{'='*60}\n", flush=True)

        if r.get('success'):
            final = extract_final_round(r['output'], args.rounds)
            print(final, flush=True)
        else:
            print(f"  FAILED: {r.get('error', 'unknown')}", flush=True)

    # Save combined report if output dir specified
    if args.output_dir:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(args.output_dir) / f"looper_combined_{ts}.md"

        report = f"""# Looper Combined Report
**Topic**: {args.topic}
**Models**: {', '.join(MODEL_LABELS[m] for m in models)}
**Rounds**: {args.rounds}
**Date**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Wall-clock time**: {total_elapsed:.1f}s
"""

        for model in models:
            r = results.get(model, {})
            label = MODEL_LABELS[model]
            report += f"\n---\n\n## {label}\n\n"
            if r.get('success'):
                report += r['output']
            else:
                report += f"**FAILED**: {r.get('error', 'unknown')}\n"

        report_path.write_text(report)
        print(f"\nCombined report saved to: {report_path}", flush=True)

    # Exit with failure if any loop failed
    if any(not r.get('success') for r in results.values()):
        failed = [MODEL_LABELS[m] for m, r in results.items() if not r.get('success')]
        print(f"\nWARNING: Failed loops: {', '.join(failed)}", file=sys.stderr)
        # Still exit 0 if at least one succeeded
        if any(r.get('success') for r in results.values()):
            sys.exit(0)
        sys.exit(1)


if __name__ == "__main__":
    main()

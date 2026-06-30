#!/usr/bin/env python3
"""
xAI Grok API Query Utility

Simple utility to query Grok 4.20 for second opinions and alternative perspectives.
Portable version for use from any Claude Code session.

Setup:
    API key loaded from (in order):
    1. ~/.claude/api-keys.env (global)
    2. .env.local (project)
    3. GROK_API_KEY environment variable
"""

import sys
import json
import subprocess
import os
from pathlib import Path

GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-4.3"  # Grok 4.3 (unified reasoning)

_api_key = None


def load_env():
    """Load environment from portable locations."""
    search_paths = [
        Path.home() / '.claude' / 'api-keys.env',  # Global skills env
        Path.cwd() / '.env.local',                  # Project override
        Path.cwd() / '.env',                        # Fallback
    ]
    for env_path in search_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
            break  # Stop after first found


def get_api_key():
    """Get API key, loading env if needed."""
    global _api_key
    if _api_key is None:
        load_env()
        _api_key = os.environ.get("GROK_API_KEY")
        if not _api_key:
            raise ValueError("GROK_API_KEY not found in ~/.claude/api-keys.env, .env.local, or environment")
    return _api_key


def query_grok(prompt: str, context: str = "") -> dict:
    """
    Query xAI Grok API with a prompt using curl.

    Args:
        prompt: The question or prompt to send to Grok
        context: Optional context to provide before the prompt

    Returns:
        dict with 'response' (str) and 'raw' (full API response)
    """
    full_prompt = f"{context}\n\n{prompt}" if context else prompt

    payload = {
        "model": GROK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful expert software architect and engineer providing second opinions, code reviews, and technical guidance. Be direct, insightful, and technically precise."
            },
            {
                "role": "user",
                "content": full_prompt
            }
        ],
        "max_tokens": 4096,
        "temperature": 0.7
    }

    try:
        payload_json = json.dumps(payload)

        api_key = get_api_key()
        curl_cmd = [
            'curl', '-s', '-S',
            '-H', f'Authorization: Bearer {api_key}',
            '-H', 'Content-Type: application/json',
            '-X', 'POST',
            '-d', payload_json,
            '--max-time', '120',
            GROK_API_URL
        ]

        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=125
        )

        if result.returncode != 0:
            return {
                'success': False,
                'error': f'curl failed: {result.stderr}',
                'raw': None
            }

        try:
            response_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'Invalid JSON response: {str(e)}\nResponse: {result.stdout[:200]}',
                'raw': None
            }

        if 'choices' in response_data and len(response_data['choices']) > 0:
            choice = response_data['choices'][0]
            if 'message' in choice and 'content' in choice['message']:
                text = choice['message']['content']
                return {
                    'success': True,
                    'response': text,
                    'raw': response_data
                }

        if 'error' in response_data:
            return {
                'success': False,
                'error': f"API error: {response_data['error'].get('message', 'Unknown error')}",
                'raw': response_data
            }

        return {
            'success': False,
            'error': 'Unexpected API response format',
            'raw': response_data
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Request timeout (>120s)',
            'raw': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error: {str(e)}',
            'raw': None
        }


def main():
    """CLI interface for querying Grok."""
    if len(sys.argv) < 2:
        print("Usage: grok_query.py <prompt> [context]", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print('  grok_query.py "How would you implement user authentication?" "Building a Flask API"', file=sys.stderr)
        sys.exit(1)

    prompt = sys.argv[1]
    context = sys.argv[2] if len(sys.argv) > 2 else ""

    result = query_grok(prompt, context)

    if result['success']:
        print(result['response'])
        sys.exit(0)
    else:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

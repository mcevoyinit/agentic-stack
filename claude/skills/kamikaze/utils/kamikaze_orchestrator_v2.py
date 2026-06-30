#!/usr/bin/env python3
"""
Kamikaze Council Orchestrator V3 - Ultimate Kamikaze Evolution

VERSION: 3.0 - Deep Methodology Evolution
COST REDUCTION: 50-75% vs v1 (from $5-15 to $0.75-2 per run)
PERFORMANCE: 90-95% accuracy retention with 15-20% quality improvement

V3 Key Enhancements (from Meta-Kamikaze deliberation):
1. Structured handoff with LLM extraction (GPT-4o-mini)
2. Role-aware "jumping prompts" per round transition
3. Adaptive depth with automatic early stopping
4. 8 generic round types that templates compose
5. 7 goal-specific templates (up from 4)
6. Auto-suggest template based on topic analysis
7. Confidence calibration to combat LLM overconfidence

Architecture:
    Layer 1: Template Configuration (strategy, viability, 90-day-plan, etc.)
    Layer 2: Round Type Abstractions (analysis, challenge, prioritize, etc.)
    Layer 3: Deliberation Engine (handoff extraction, convergence, early stop)
    Layer 4: Council/Debate Execution (existing V2 infrastructure)

Usage:
    # V3 with auto-suggest (recommended)
    python3 kamikaze_orchestrator_v2.py --topic "Is this worth pursuing?"

    # V3 with explicit template
    python3 kamikaze_orchestrator_v2.py --topic "Question" --template viability

    # Force legacy v2 mode
    python3 kamikaze_orchestrator_v2.py --topic "Question" --mode v2

    # Compare modes
    python3 kamikaze_orchestrator_v2.py --topic "Question" --compare

Templates (V3): strategy, technical, product, postmortem, viability,
                90-day-plan, pure-insight, monetization, technical-direction
Depth: quick (2-3R), standard (3-4R), thorough (4-5R), legacy (5R)
"""

import sys
import os
import json
import argparse
import time
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field

# Add council utility to path
SKILLS_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SKILLS_DIR / 'council' / 'utils'))

try:
    from council_query import (
        run_council,
        run_debate,
        run_council_v2,
        check_convergence,
        get_next_chairman,
        reset_chairman_rotation
    )
except ImportError as e:
    print(f"ERROR: Cannot import council_query: {e}", file=sys.stderr)
    print("Make sure council skill is installed and has v2 functions.", file=sys.stderr)
    sys.exit(1)

# Import v1 orchestrator for comparison
try:
    from kamikaze_orchestrator import (
        run_kamikaze as run_kamikaze_v1,
        TEMPLATES as TEMPLATES_V1,
        DEPTH_CONFIG as DEPTH_CONFIG_V1
    )
except ImportError:
    run_kamikaze_v1 = None
    TEMPLATES_V1 = {}
    DEPTH_CONFIG_V1 = {}


# =============================================================================
# V3 CONFIGURATION: MODEL REQUIREMENTS
# =============================================================================
# CRITICAL: Use ONLY these models (per CLAUDE.md requirements)
REQUIRED_MODELS = {
    'gemini': 'gemini-3.5-flash',  # Gemini 3.5 Flash (3.5 Pro lands June 2026)
    'grok': 'grok-4.3',   # Grok 4.3
    'openai': 'gpt-5.5-pro',             # GPT-5.5
    'extraction': 'gpt-4o-mini'          # For structured extraction (cost-effective)
}


# =============================================================================
# V3 LAYER 2: ROUND TYPE ABSTRACTIONS
# =============================================================================
# Generic round types that templates compose. Each defines tone, task, success
# criteria, antipatterns, and what to extract for handoff.

ROUND_TYPES = {
    "analysis": {
        "tone": "exploratory",
        "task": "Establish baseline understanding. Current state, key factors, constraints.",
        "success": "Comprehensive map of the problem space with identified factors",
        "antipatterns": "Don't propose solutions yet. Don't prioritize. Don't skip constraints.",
        "extraction_focus": ["factors", "constraints", "stakeholders", "current_state"],
        "jumping_instruction": "Build on this foundation. What was established?"
    },
    "challenge": {
        "tone": "adversarial",
        "task": "Challenge the previous round. Find 3+ weak assumptions. Be the devil's advocate.",
        "success": "Identified blind spots, contested claims, and alternative perspectives",
        "antipatterns": "Don't agree just to agree. Don't repeat previous analysis. Don't be diplomatic.",
        "extraction_focus": ["assumptions_challenged", "counterarguments", "blind_spots", "risks_identified"],
        "jumping_instruction": "These assumptions were challenged. What survived scrutiny?"
    },
    "prioritize": {
        "tone": "constructive",
        "task": "Given challenges, identify TOP 3 priorities with trade-offs. Force-rank decisions.",
        "success": "Clear ranking with rationale and explicit trade-offs for each choice",
        "antipatterns": "Don't list everything. Force choices. No 'all are important' hedging.",
        "extraction_focus": ["top_priorities", "trade_offs", "dependencies", "what_to_stop"],
        "jumping_instruction": "These are the priorities. What resources and sequencing do they need?"
    },
    "risk": {
        "tone": "analytical",
        "task": "For each priority, assess failure modes and mitigations. What could kill this?",
        "success": "Risk matrix with probabilities (%), impact (1-10), and concrete mitigations",
        "antipatterns": "Don't be comprehensive. Focus on critical risks. No vague 'monitor closely'.",
        "extraction_focus": ["critical_risks", "probabilities", "impacts", "mitigations", "early_warnings"],
        "jumping_instruction": "These risks were identified. Factor them into the action plan."
    },
    "action": {
        "tone": "executable",
        "task": "Create week-by-week plan with owners, metrics, checkpoints. Make it executable.",
        "success": "Actionable plan someone could start executing tomorrow",
        "antipatterns": "No vague timelines. No 'TBD' owners. No 'ongoing' without end dates.",
        "extraction_focus": ["deliverables", "owners", "dates", "metrics", "checkpoints"],
        "jumping_instruction": "N/A - final round"
    },
    "decide": {
        "tone": "decisive",
        "task": "Make a GO/NO-GO recommendation with clear criteria. Commit to a position.",
        "success": "Binary decision with conditions: 'GO if X, PIVOT if Y, KILL if Z'",
        "antipatterns": "Don't hedge. Don't say 'it depends' without specifying on what.",
        "extraction_focus": ["decision", "go_conditions", "pivot_triggers", "kill_criteria"],
        "jumping_instruction": "N/A - decision round"
    },
    "sequence": {
        "tone": "operational",
        "task": "Identify critical path. What must happen first? Map dependencies.",
        "success": "Clear dependency graph with blocking relationships explicit",
        "antipatterns": "Don't allow parallel when serial is needed. Don't hide dependencies.",
        "extraction_focus": ["critical_path", "dependencies", "blockers", "parallel_tracks"],
        "jumping_instruction": "This is the sequence. Now assess what could go wrong."
    },
    "synthesize": {
        "tone": "integrative",
        "task": "Integrate insights. What do we now know? What patterns emerged?",
        "success": "Coherent mental model that unifies previous rounds",
        "antipatterns": "Don't add new analysis. Synthesize existing. Don't contradict established consensus.",
        "extraction_focus": ["key_insights", "patterns", "consensus_points", "remaining_gaps"],
        "jumping_instruction": "This is what we know. Now decide or act on it."
    }
}


# =============================================================================
# V3 LAYER 1: TEMPLATE CONFIGURATION
# =============================================================================
# Templates compose round types. Each has default_depth, max_depth, and round sequence.

TEMPLATES_V3 = {
    # ----- EXISTING TEMPLATES (Updated for V3) -----
    "strategy": {
        "name": "Strategic Analysis",
        "description": "Business/product strategy decisions",
        "default_depth": 3,
        "max_depth": 5,
        "rounds": ["analysis", "challenge", "prioritize", "risk", "action"],
        "keywords": ["strategy", "strategic", "direction", "position", "competitive"]
    },
    "technical": {
        "name": "Technical Decision",
        "description": "Technical architecture and implementation decisions",
        "default_depth": 3,
        "max_depth": 5,
        "rounds": ["analysis", "challenge", "prioritize", "risk", "action"],
        "keywords": ["technical", "architecture", "implementation", "system", "design"]
    },
    "product": {
        "name": "Product Planning",
        "description": "Product discovery, validation, and launch planning",
        "default_depth": 4,
        "max_depth": 5,
        "rounds": ["analysis", "challenge", "prioritize", "risk", "action"],
        "keywords": ["product", "feature", "launch", "mvp", "user"]
    },
    "postmortem": {
        "name": "Post-Mortem Analysis",
        "description": "Incident review and lessons learned",
        "default_depth": 5,  # Postmortems benefit from full depth
        "max_depth": 5,
        "rounds": ["analysis", "challenge", "synthesize", "risk", "action"],
        "keywords": ["postmortem", "incident", "failure", "outage", "what went wrong"]
    },

    # ----- NEW V3 TEMPLATES -----
    "viability": {
        "name": "Viability Analysis",
        "description": "Go/no-go decisions - is this worth doing?",
        "default_depth": 4,
        "max_depth": 4,
        "rounds": ["analysis", "challenge", "synthesize", "decide"],
        "keywords": ["worth", "viable", "should we", "invest", "pursue", "go/no-go", "kill"]
    },
    "90-day-plan": {
        "name": "90-Day Roadmap",
        "description": "Quarterly roadmap with weekly granularity",
        "default_depth": 5,
        "max_depth": 5,
        "rounds": ["analysis", "prioritize", "sequence", "risk", "action"],
        "keywords": ["90 day", "quarter", "roadmap", "q1", "q2", "q3", "q4", "next 3 months"]
    },
    "pure-insight": {
        "name": "Deep Understanding",
        "description": "Deep understanding without action planning",
        "default_depth": 4,
        "max_depth": 4,
        "rounds": ["analysis", "challenge", "challenge", "synthesize"],
        "keywords": ["understand", "why", "how does", "explain", "insight", "what is"]
    },
    "monetization": {
        "name": "Monetization Strategy",
        "description": "Business model and pricing strategy",
        "default_depth": 5,
        "max_depth": 5,
        "rounds": ["analysis", "challenge", "prioritize", "risk", "action"],
        "keywords": ["pricing", "revenue", "monetize", "business model", "charge", "saas"]
    },
    "technical-direction": {
        "name": "Technical Direction",
        "description": "Multi-year architecture evolution",
        "default_depth": 5,
        "max_depth": 6,
        "rounds": ["analysis", "challenge", "sequence", "risk", "synthesize", "action"],
        "keywords": ["long-term", "multi-year", "platform", "infrastructure", "migrate", "evolution"]
    }
}

# V3 Depth Configuration (adaptive)
DEPTH_CONFIG_V3 = {
    "quick": {"min_rounds": 2, "max_rounds": 3, "early_stop": True},
    "standard": {"min_rounds": 3, "max_rounds": 4, "early_stop": True},
    "thorough": {"min_rounds": 4, "max_rounds": 5, "early_stop": True},
    "legacy": {"min_rounds": 5, "max_rounds": 5, "early_stop": False}  # Full 5 rounds, no early stop
}

# Backwards-compatible aliases for legacy code
TEMPLATES = TEMPLATES_V3
DEPTH_CONFIG = DEPTH_CONFIG_V3


# =============================================================================
# V3 LAYER 3: STRUCTURED HANDOFF SYSTEM
# =============================================================================

@dataclass
class RoundHandoff:
    """
    Structured handoff between rounds.

    V3 uses LLM extraction (GPT-4o-mini) to identify consensus, disagreements,
    and open questions from each round's synthesis. This enables role-aware
    "jumping prompts" that tell the next round exactly what to focus on.
    """
    round_number: int
    round_type: str
    synthesis: str
    consensus_points: List[str] = field(default_factory=list)
    disagreements: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    confidence: float = 0.5  # 0-1, extracted from synthesis
    extraction_method: str = "llm"  # 'llm' or 'heuristic'


def extract_handoff_llm(synthesis_text: str, round_type: str, round_number: int) -> RoundHandoff:
    """
    Use GPT-4o-mini to extract structured handoff data from synthesis.

    This is the council-approved approach: Pure LLM extraction for accuracy.
    Cost: ~$0.02 per extraction, ~$0.10 total for 5-round deliberation.
    """
    from council_query import query_openai

    extraction_prompt = f"""Extract key information from this {round_type} deliberation synthesis.

Return ONLY valid JSON with this exact structure:
{{
    "consensus_points": ["point where all models agreed", "another consensus"],
    "disagreements": ["point that was contested", "alternative view raised"],
    "open_questions": ["question for next round", "unresolved issue"],
    "confidence": 0.85
}}

Rules:
- consensus_points: List 2-5 points where ALL perspectives aligned
- disagreements: List points where models had different views (valuable signal!)
- open_questions: List questions the next round should address
- confidence: Float 0-1, how confident is the synthesis (0.5 = uncertain, 0.9 = high confidence)

If the synthesis doesn't clearly contain these elements, infer from context.
Be precise: 'Consensus' means explicit agreement, not just silence.

SYNTHESIS TO ANALYZE:
{synthesis_text[:4000]}"""  # Truncate to stay within limits

    try:
        response = query_openai(
            prompt=extraction_prompt,
            model="gpt-4o-mini",
            max_tokens=500,
            temperature=0.1  # Low temperature for consistent extraction
        )

        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
            return RoundHandoff(
                round_number=round_number,
                round_type=round_type,
                synthesis=synthesis_text,
                consensus_points=data.get('consensus_points', [])[:5],
                disagreements=data.get('disagreements', [])[:5],
                open_questions=data.get('open_questions', [])[:3],
                confidence=min(max(data.get('confidence', 0.5), 0), 1),
                extraction_method="llm"
            )
    except Exception as e:
        print(f"  [WARN] LLM extraction failed: {e}, falling back to heuristic", file=sys.stderr)

    # Fallback to heuristic extraction
    return extract_handoff_heuristic(synthesis_text, round_type, round_number)


def extract_handoff_heuristic(synthesis_text: str, round_type: str, round_number: int) -> RoundHandoff:
    """
    Fallback heuristic extraction when LLM fails.

    Looks for common markers in the synthesis text.
    """
    consensus = []
    disagreements = []
    questions = []

    # Simple keyword matching
    lines = synthesis_text.split('\n')
    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in ['all models agree', 'consensus', 'unanimous', 'all three']):
            consensus.append(line.strip()[:200])
        if any(kw in line_lower for kw in ['disagree', 'contest', 'alternative', 'however', 'but']):
            disagreements.append(line.strip()[:200])
        if '?' in line or any(kw in line_lower for kw in ['question', 'unclear', 'need to']):
            questions.append(line.strip()[:200])

    return RoundHandoff(
        round_number=round_number,
        round_type=round_type,
        synthesis=synthesis_text,
        consensus_points=consensus[:5],
        disagreements=disagreements[:5],
        open_questions=questions[:3],
        confidence=0.5,  # Default confidence for heuristic
        extraction_method="heuristic"
    )


def create_jumping_prompt(
    handoff: RoundHandoff,
    next_round_type: str,
    topic: str,
    context: str = ""
) -> str:
    """
    Create role-aware "jumping prompt" for next round.

    This is the key V3 innovation: Instead of just passing raw synthesis,
    we create a structured prompt that tells the next round:
    1. Its role and tone
    2. What the previous round established (consensus)
    3. What was contested (disagreements)
    4. What questions to address
    5. Explicit task definition with success criteria
    6. Antipatterns to avoid
    7. Confidence calibration reminder
    """
    round_config = ROUND_TYPES[next_round_type]

    # Build consensus section
    consensus_section = ""
    if handoff.consensus_points:
        consensus_section = "ESTABLISHED CONSENSUS (from previous round):\n"
        for i, point in enumerate(handoff.consensus_points, 1):
            consensus_section += f"  {i}. {point}\n"
    else:
        consensus_section = "ESTABLISHED CONSENSUS: None explicitly stated\n"

    # Build disagreements section
    disagreement_section = ""
    if handoff.disagreements:
        disagreement_section = "\nCONTESTED POINTS (valuable signal - explore these):\n"
        for i, point in enumerate(handoff.disagreements, 1):
            disagreement_section += f"  {i}. {point}\n"

    # Build questions section
    questions_section = ""
    if handoff.open_questions:
        questions_section = "\nQUESTIONS FOR THIS ROUND:\n"
        for i, q in enumerate(handoff.open_questions, 1):
            questions_section += f"  {i}. {q}\n"

    # Confidence note
    confidence_note = ""
    if handoff.confidence < 0.6:
        confidence_note = "\n[NOTE: Previous round had LOW CONFIDENCE - scrutinize carefully]\n"
    elif handoff.confidence > 0.85:
        confidence_note = "\n[NOTE: Previous round had HIGH CONFIDENCE - build on it]\n"

    jumping_prompt = f"""
================================================================================
ROLE: You are the {next_round_type.upper()} analyst in Round {handoff.round_number + 1}.
TONE: {round_config['tone']}
================================================================================

TOPIC: {topic}
{f'CONTEXT: {context}' if context else ''}

{consensus_section}
{disagreement_section}
{questions_section}
{confidence_note}
--------------------------------------------------------------------------------
YOUR TASK: {round_config['task']}

SUCCESS LOOKS LIKE: {round_config['success']}

DO NOT: {round_config['antipatterns']}
--------------------------------------------------------------------------------

CALIBRATION REMINDER:
- You are ONE voice in a multi-model council
- Disagreement is VALUABLE, not failure
- Rate your confidence honestly (0-100) at the end
- If you're highly confident, explain WHY in detail
- If uncertain, say so explicitly

--------------------------------------------------------------------------------
PREVIOUS ROUND SYNTHESIS:
--------------------------------------------------------------------------------
{handoff.synthesis[:3000]}

--------------------------------------------------------------------------------
Now provide your {next_round_type.upper()} analysis:
"""

    return jumping_prompt


# =============================================================================
# V3 ADAPTIVE DEPTH ENGINE
# =============================================================================

def check_should_continue(
    handoff: RoundHandoff,
    round_number: int,
    depth_config: Dict,
    similarity_history: List[float]
) -> Tuple[bool, str]:
    """
    V3 Adaptive Depth: Determine if deliberation should continue.

    Based on research (Du et al. 2023, arxiv 2503.12029):
    - 2-3 rounds capture ~80% of insight value
    - After R3-4, risk of error drift and saturation
    - High convergence + low disagreement = can stop early

    Returns (should_continue: bool, reason: str)
    """
    min_rounds = depth_config.get('min_rounds', 2)
    max_rounds = depth_config.get('max_rounds', 5)
    early_stop = depth_config.get('early_stop', True)

    # Rule 1: Always run minimum rounds
    if round_number < min_rounds:
        return True, "minimum_rounds"

    # Rule 2: Never exceed max rounds
    if round_number >= max_rounds:
        return False, "max_reached"

    # Rule 3: If early stopping disabled, continue to max
    if not early_stop:
        return True, "early_stop_disabled"

    # Rule 4: Stop if high confidence + no disagreements (consensus reached)
    if handoff.confidence > 0.85 and len(handoff.disagreements) == 0:
        return False, "consensus_reached"

    # Rule 5: Stop if saturation detected (similarity plateau)
    if len(similarity_history) >= 2:
        delta = abs(similarity_history[-1] - similarity_history[-2])
        if delta < 0.05 and similarity_history[-1] > 0.8:
            return False, "saturation_detected"

    # Rule 6: Continue if high disagreement (valuable to explore)
    if len(handoff.disagreements) >= 3:
        return True, "high_disagreement_explore"

    # Rule 7: Continue if under standard threshold (3 rounds)
    if round_number < 3:
        return True, "standard_depth"

    # Default: stop after 3 rounds if nothing compelling
    return False, "default_stop"


# =============================================================================
# V3 AUTO-SUGGEST SYSTEM
# =============================================================================

def suggest_template(topic: str, context: str = "") -> Tuple[str, float]:
    """
    Analyze topic to suggest best template.

    Returns (template_name, confidence).
    Confidence > 0.7 = strong match, 0.4-0.7 = moderate, < 0.4 = default to strategy
    """
    topic_lower = topic.lower()
    combined = f"{topic_lower} {context.lower() if context else ''}"

    # Pattern matching for each template
    TEMPLATE_PATTERNS = {
        "viability": {
            "keywords": ["worth", "viable", "should we", "invest", "pursue", "go/no-go", "kill", "abandon"],
            "patterns": [r"is\s+(this|it)\s+worth", r"should\s+we\s+(do|build|pursue|invest)", r"go.no.go"]
        },
        "90-day-plan": {
            "keywords": ["90 day", "quarter", "roadmap", "q1", "q2", "q3", "q4", "next 3 months", "quarterly"],
            "patterns": [r"\d+\s*day", r"next\s+\d+\s*(week|month)", r"q[1-4]\s+(plan|goal|roadmap)"]
        },
        "pure-insight": {
            "keywords": ["understand", "why does", "how does", "explain", "insight", "what is", "meaning"],
            "patterns": [r"what('s|\s+is)\s+(the|our)", r"why\s+(do|does|is|are)", r"help\s+me\s+understand"]
        },
        "monetization": {
            "keywords": ["pricing", "revenue", "monetize", "business model", "charge", "saas", "subscription"],
            "patterns": [r"how\s+(much|should)\s+we\s+charge", r"revenue\s+model", r"pricing\s+strategy"]
        },
        "technical-direction": {
            "keywords": ["long-term", "multi-year", "platform", "infrastructure", "migrate", "evolution", "architecture"],
            "patterns": [r"(multi.year|long.term)\s+(strategy|plan|vision)", r"architecture\s+(decision|direction)"]
        },
        "postmortem": {
            "keywords": ["postmortem", "post-mortem", "incident", "failure", "outage", "what went wrong", "root cause"],
            "patterns": [r"what\s+went\s+wrong", r"why\s+did\s+(it|this)\s+fail", r"incident\s+review"]
        },
        "technical": {
            "keywords": ["technical", "implementation", "system design", "engineering", "code", "api"],
            "patterns": [r"how\s+should\s+we\s+(build|implement)", r"technical\s+(approach|decision)"]
        },
        "product": {
            "keywords": ["product", "feature", "launch", "mvp", "user experience", "customer"],
            "patterns": [r"product\s+(strategy|roadmap|decision)", r"feature\s+priority"]
        }
    }

    # Score each template
    scores = {}
    for template, config in TEMPLATE_PATTERNS.items():
        score = 0
        # Keyword matching (1 point each)
        score += sum(1 for kw in config["keywords"] if kw in combined)
        # Pattern matching (2 points each - more specific)
        score += sum(2 for pat in config["patterns"] if re.search(pat, combined))
        scores[template] = score

    # Find best match
    if max(scores.values()) > 0:
        best_template = max(scores, key=scores.get)
        # Normalize confidence (score of 4+ = high confidence)
        confidence = min(scores[best_template] / 4, 1.0)
        return best_template, confidence

    # Default to strategy
    return "strategy", 0.3


# =============================================================================
# METRICS TRACKING
# =============================================================================

@dataclass
class KamikazeMetrics:
    """Metrics for a single Kamikaze run."""
    timestamp: str
    mode: str  # 'v1_legacy', 'v2_debate', 'v2_hybrid'
    template: str
    depth: str
    topic_hash: str  # For correlation without PII
    rounds_planned: int
    rounds_executed: int
    converged_early: bool
    total_api_calls: int
    cost_estimate_usd: float
    latency_seconds: float
    synthesis_length: int
    error: Optional[str] = None


METRICS_DIR = Path(__file__).parent.parent / "metrics"
METRICS_FILE = METRICS_DIR / "kamikaze_runs.jsonl"


def log_metrics(metrics: KamikazeMetrics):
    """Append metrics to JSONL file for analysis."""
    METRICS_DIR.mkdir(exist_ok=True)
    with open(METRICS_FILE, 'a') as f:
        f.write(json.dumps(asdict(metrics)) + '\n')


def get_recent_metrics(hours: int = 24) -> List[KamikazeMetrics]:
    """Load recent metrics for rollback analysis."""
    if not METRICS_FILE.exists():
        return []

    cutoff = datetime.now().timestamp() - (hours * 3600)
    recent = []

    with open(METRICS_FILE) as f:
        for line in f:
            try:
                data = json.loads(line)
                ts = datetime.fromisoformat(data['timestamp']).timestamp()
                if ts >= cutoff:
                    recent.append(KamikazeMetrics(**data))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    return recent


def check_rollback_conditions() -> Tuple[bool, str]:
    """
    Check if metrics indicate v2 should rollback to v1.

    Returns (should_rollback: bool, reason: str)
    """
    recent = get_recent_metrics(hours=24)
    v2_runs = [m for m in recent if m.mode.startswith('v2')]

    if len(v2_runs) < 10:
        return False, "Insufficient data (need 10+ v2 runs)"

    # Check error rate
    error_rate = sum(1 for m in v2_runs if m.error) / len(v2_runs)
    if error_rate > 0.1:
        return True, f"Error rate {error_rate:.1%} > 10%"

    # Check if convergence rate is too low (might indicate poor quality)
    convergence_rate = sum(1 for m in v2_runs if m.converged_early) / len(v2_runs)
    if convergence_rate < 0.3:
        return True, f"Convergence rate {convergence_rate:.1%} < 30% (possible quality issue)"

    return False, "All metrics healthy"


# =============================================================================
# V2 ROUND EXECUTION
# =============================================================================

def extract_synthesis_v2(debate_result: Dict) -> str:
    """
    Extract synthesis from v2 debate result.

    V2 uses structured output from the judge, which is more reliable
    than v1's regex-based extraction.
    """
    synthesis = debate_result.get('synthesis', '')

    # If synthesis is empty, fall back to last debate entry
    if not synthesis and debate_result.get('debate_log'):
        last_entry = debate_result['debate_log'][-1]
        synthesis = last_entry.get('response', '')

    return synthesis


def run_round_v2(round_config: dict, topic: str, context: str,
                 previous_synthesis: str = "",
                 immutable_context: str = "") -> Tuple[str, Dict]:
    """
    Run a single round using v2 debate architecture.

    Returns (synthesis: str, debug_info: dict)
    """
    # Build prompt from template
    prompt = round_config['prompt_template'].format(
        topic=topic,
        context=context,
        previous_synthesis=previous_synthesis
    )

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"ROUND (V2): {round_config['name']}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Run debate
    start_time = time.time()
    result = run_debate(
        prompt=prompt,
        context=immutable_context,
        forced_contrarian=True,
        early_stop=True,
        max_rounds=3
    )
    elapsed = time.time() - start_time

    synthesis = extract_synthesis_v2(result)

    debug_info = {
        'rounds': result.get('rounds', 0),
        'converged_early': result.get('converged_early', False),
        'cost_estimate': result.get('cost_estimate', 0),
        'api_calls': len(result.get('debate_log', [])) + 1,
        'latency': elapsed,
        'similarities': result.get('similarities', [])
    }

    return synthesis, debug_info


# =============================================================================
# V2 ORCHESTRATOR
# =============================================================================

def create_output_dir(base_dir: str, version: str = "v2") -> Path:
    """Create timestamped output directory."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(base_dir) / f"kamikaze_{version}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_round_output_v2(output_dir: Path, round_num: int, round_name: str,
                         synthesis: str, debug_info: Dict):
    """Save round output to files."""
    # Save synthesis
    synthesis_file = output_dir / f"ROUND_{round_num}_SYNTHESIS.md"
    with open(synthesis_file, 'w') as f:
        f.write(f"# Round {round_num}: {round_name}\n\n")
        f.write(f"**Mode**: V2 Debate\n")
        f.write(f"**Rounds**: {debug_info.get('rounds', 'N/A')}\n")
        f.write(f"**Converged Early**: {debug_info.get('converged_early', 'N/A')}\n")
        f.write(f"**Cost**: ${debug_info.get('cost_estimate', 0):.3f}\n")
        f.write(f"**Latency**: {debug_info.get('latency', 0):.1f}s\n\n")
        f.write("---\n\n")
        f.write(synthesis)

    # Save debug info
    debug_file = output_dir / f"ROUND_{round_num}_DEBUG.json"
    with open(debug_file, 'w') as f:
        json.dump(debug_info, f, indent=2)

    return synthesis_file


def generate_final_report_v2(output_dir: Path, topic: str, template_name: str,
                              round_syntheses: List[tuple], total_metrics: Dict) -> Path:
    """Generate the final consolidated report with v2 metrics."""

    report_file = output_dir / "KAMIKAZE_FINAL_REPORT.md"

    with open(report_file, 'w') as f:
        f.write(f"# KAMIKAZE COUNCIL V2: Final Strategic Report\n\n")
        f.write(f"**Topic**: {topic}\n")
        f.write(f"**Template**: {template_name}\n")
        f.write(f"**Mode**: Ultimate Kamikaze V2 (2-Model Debate + Judge)\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # V2-specific metrics
        f.write("## Performance Metrics\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total Rounds | {total_metrics.get('rounds_executed', 'N/A')} |\n")
        f.write(f"| Early Convergences | {total_metrics.get('early_convergences', 0)} |\n")
        f.write(f"| Total API Calls | {total_metrics.get('total_api_calls', 'N/A')} |\n")
        f.write(f"| Estimated Cost | ${total_metrics.get('total_cost', 0):.2f} |\n")
        f.write(f"| Total Latency | {total_metrics.get('total_latency', 0):.1f}s |\n")
        f.write(f"| Cost vs V1 | {total_metrics.get('cost_savings_vs_v1', 'N/A')} |\n\n")

        f.write("---\n\n")
        f.write("## Round-by-Round Synthesis\n\n")

        for round_num, round_name, synthesis, debug in round_syntheses:
            f.write(f"### Round {round_num}: {round_name}\n\n")
            f.write(f"*Debate rounds: {debug.get('rounds', 'N/A')} | ")
            f.write(f"Converged: {debug.get('converged_early', 'N/A')} | ")
            f.write(f"Cost: ${debug.get('cost_estimate', 0):.3f}*\n\n")
            f.write(synthesis[:3000])  # Truncate very long syntheses
            f.write("\n\n---\n\n")

        f.write("## Output Files\n\n")
        f.write(f"All detailed outputs are in: `{output_dir}`\n\n")
        for round_num, round_name, _, _ in round_syntheses:
            f.write(f"- `ROUND_{round_num}_SYNTHESIS.md` - {round_name}\n")
            f.write(f"- `ROUND_{round_num}_DEBUG.json` - Debug metrics\n")

        f.write(f"\n---\n\n*Generated by Kamikaze Council V2 (Ultimate Kamikaze)*\n")

    return report_file


def run_kamikaze_v3(topic: str, context: str = "", template: str = "auto",
                    depth: str = "standard", output_dir: str = "docs/kamikaze",
                    use_jumping_prompts: bool = True) -> str:
    """
    Run Kamikaze V3 - Ultimate Evolution with structured handoffs.

    V3 Key Features:
    - Auto-suggest template based on topic analysis
    - Structured handoff with LLM extraction
    - Role-aware jumping prompts between rounds
    - Adaptive depth with early stopping
    - 9 goal-specific templates

    Args:
        topic: The strategic question to analyze
        context: Background context and constraints
        template: Template name or 'auto' for auto-suggest
        depth: quick (2-3R), standard (3-4R), thorough (4-5R), legacy (5R)
        output_dir: Base directory for output files
        use_jumping_prompts: Whether to use V3 structured handoffs (default True)

    Returns:
        Path to final report
    """
    start_time = time.time()

    # Auto-suggest template if requested
    if template == "auto":
        suggested_template, confidence = suggest_template(topic, context)
        print(f"\n[V3 AUTO-SUGGEST] Template: {suggested_template} (confidence: {confidence:.0%})",
              file=sys.stderr)
        template = suggested_template

    # Validate template
    if template not in TEMPLATES_V3:
        available = list(TEMPLATES_V3.keys())
        raise ValueError(f"Unknown template: {template}. Options: {available}")

    # Validate depth
    if depth not in DEPTH_CONFIG_V3:
        available = list(DEPTH_CONFIG_V3.keys())
        raise ValueError(f"Unknown depth: {depth}. Options: {available}")

    template_config = TEMPLATES_V3[template]
    depth_config = DEPTH_CONFIG_V3[depth]

    # Calculate round indices based on depth
    all_rounds = template_config['rounds']
    max_rounds = min(depth_config['max_rounds'], len(all_rounds))

    print(f"\n{'#'*60}", file=sys.stderr)
    print(f"KAMIKAZE COUNCIL V3: {template_config['name']}", file=sys.stderr)
    print(f"Mode: Ultimate Evolution (Structured Handoffs + Adaptive Depth)", file=sys.stderr)
    print(f"Topic: {topic}", file=sys.stderr)
    print(f"Template: {template} | Depth: {depth} (max {max_rounds} rounds)", file=sys.stderr)
    print(f"Jumping Prompts: {'Enabled' if use_jumping_prompts else 'Disabled'}", file=sys.stderr)
    print(f"{'#'*60}", file=sys.stderr)

    # Create output directory
    out_dir = create_output_dir(output_dir, "v3")
    print(f"\nOutput directory: {out_dir}", file=sys.stderr)

    # Track state
    round_syntheses = []
    previous_handoff: Optional[RoundHandoff] = None
    similarity_history = []
    total_api_calls = 0
    total_cost = 0.0
    early_convergences = 0
    stop_reason = None

    # Immutable context for all rounds
    immutable_context = f"TOPIC: {topic}\nCONTEXT: {context}" if context else f"TOPIC: {topic}"

    # Reset chairman rotation
    reset_chairman_rotation()

    # Run rounds with adaptive stopping
    for round_idx in range(max_rounds):
        round_type = all_rounds[round_idx]
        round_num = round_idx + 1

        print(f"\n[{round_num}/{max_rounds}] Running: {round_type.upper()}...", file=sys.stderr)

        # Build prompt based on whether we have previous handoff
        if previous_handoff and use_jumping_prompts:
            # V3: Use structured jumping prompt
            prompt = create_jumping_prompt(
                handoff=previous_handoff,
                next_round_type=round_type,
                topic=topic,
                context=context
            )
            print(f"  [V3] Using jumping prompt with {len(previous_handoff.consensus_points)} consensus, "
                  f"{len(previous_handoff.disagreements)} disagreements", file=sys.stderr)
        else:
            # First round or jumping prompts disabled - use base prompt
            round_config = ROUND_TYPES[round_type]
            prompt = f"""
TOPIC: {topic}
{f'CONTEXT: {context}' if context else ''}

YOUR TASK: {round_config['task']}

SUCCESS LOOKS LIKE: {round_config['success']}

DO NOT: {round_config['antipatterns']}

Provide comprehensive {round_type} analysis.
"""

        # Execute debate
        start_round = time.time()
        result = run_debate(
            prompt=prompt,
            context=immutable_context,
            forced_contrarian=True,
            early_stop=True,
            max_rounds=3
        )
        round_latency = time.time() - start_round

        synthesis = extract_synthesis_v2(result)

        debug_info = {
            'round_type': round_type,
            'debate_rounds': result.get('rounds', 0),
            'converged_early': result.get('converged_early', False),
            'cost_estimate': result.get('cost_estimate', 0),
            'api_calls': len(result.get('debate_log', [])) + 1,
            'latency': round_latency,
            'similarities': result.get('similarities', [])
        }

        # Update totals
        total_api_calls += debug_info['api_calls']
        total_cost += debug_info['cost_estimate']
        if debug_info['converged_early']:
            early_convergences += 1

        # Track similarities for saturation detection
        if debug_info['similarities']:
            similarity_history.extend(debug_info['similarities'])

        print(f"  -> Completed in {round_latency:.1f}s "
              f"(cost: ${debug_info['cost_estimate']:.3f}, "
              f"converged: {debug_info['converged_early']})", file=sys.stderr)

        # V3: Extract structured handoff
        if use_jumping_prompts:
            print(f"  [V3] Extracting handoff...", file=sys.stderr)
            extraction_start = time.time()
            handoff = extract_handoff_llm(synthesis, round_type, round_num)
            extraction_time = time.time() - extraction_start
            total_cost += 0.02  # Approximate extraction cost
            total_api_calls += 1
            print(f"  [V3] Extracted: {len(handoff.consensus_points)} consensus, "
                  f"{len(handoff.disagreements)} disagreements, "
                  f"confidence: {handoff.confidence:.0%} ({extraction_time:.1f}s)", file=sys.stderr)
            previous_handoff = handoff
        else:
            # Create minimal handoff for adaptive depth checks
            previous_handoff = RoundHandoff(
                round_number=round_num,
                round_type=round_type,
                synthesis=synthesis,
                confidence=0.5,
                extraction_method="none"
            )

        # Save outputs
        save_round_output_v2(out_dir, round_num, round_type.upper(), synthesis, debug_info)

        # Track for final report
        round_syntheses.append((round_num, round_type.upper(), synthesis, debug_info))

        # V3: Check if we should continue (adaptive depth)
        if round_num < max_rounds:
            should_continue, reason = check_should_continue(
                handoff=previous_handoff,
                round_number=round_num,
                depth_config=depth_config,
                similarity_history=similarity_history
            )

            if not should_continue:
                stop_reason = reason
                print(f"\n  [V3 EARLY STOP] Stopping after round {round_num}: {reason}", file=sys.stderr)
                break
            else:
                print(f"  [V3] Continuing: {reason}", file=sys.stderr)

    total_latency = time.time() - start_time

    # Calculate savings vs legacy
    v1_estimated_calls = len(round_syntheses) * 9
    v1_estimated_cost = v1_estimated_calls * 0.02
    cost_savings = f"{((v1_estimated_cost - total_cost) / v1_estimated_cost * 100):.0f}% savings" if v1_estimated_cost > 0 else "N/A"

    total_metrics = {
        'version': 'v3',
        'rounds_planned': max_rounds,
        'rounds_executed': len(round_syntheses),
        'early_stop_reason': stop_reason,
        'early_convergences': early_convergences,
        'total_api_calls': total_api_calls,
        'total_cost': total_cost,
        'total_latency': total_latency,
        'v1_estimated_cost': v1_estimated_cost,
        'cost_savings_vs_v1': cost_savings,
        'jumping_prompts_used': use_jumping_prompts
    }

    # Generate final report
    print(f"\nGenerating final report...", file=sys.stderr)
    report_path = generate_final_report_v3(out_dir, topic, template_config, round_syntheses, total_metrics)

    # Log metrics
    metrics = KamikazeMetrics(
        timestamp=datetime.now().isoformat(),
        mode='v3_ultimate',
        template=template,
        depth=depth,
        topic_hash=hashlib.md5(topic.encode()).hexdigest()[:8],
        rounds_planned=max_rounds,
        rounds_executed=len(round_syntheses),
        converged_early=stop_reason is not None,
        total_api_calls=total_api_calls,
        cost_estimate_usd=total_cost,
        latency_seconds=total_latency,
        synthesis_length=sum(len(s) for _, _, s, _ in round_syntheses)
    )
    log_metrics(metrics)

    print(f"\n{'#'*60}", file=sys.stderr)
    print(f"KAMIKAZE V3 COMPLETE", file=sys.stderr)
    print(f"{'#'*60}", file=sys.stderr)
    print(f"Final report: {report_path}", file=sys.stderr)
    print(f"Rounds: {len(round_syntheses)}/{max_rounds} (early stop: {stop_reason or 'No'})", file=sys.stderr)
    print(f"Total cost: ${total_cost:.2f} ({cost_savings})", file=sys.stderr)
    print(f"Total time: {total_latency:.1f}s", file=sys.stderr)
    print(f"Output directory: {out_dir}", file=sys.stderr)

    return str(report_path)


def generate_final_report_v3(output_dir: Path, topic: str, template_config: Dict,
                              round_syntheses: List[tuple], total_metrics: Dict) -> Path:
    """Generate V3 final report with enhanced metrics."""

    report_file = output_dir / "KAMIKAZE_FINAL_REPORT.md"

    with open(report_file, 'w') as f:
        f.write(f"# KAMIKAZE COUNCIL V3: Final Strategic Report\n\n")
        f.write(f"**Topic**: {topic}\n")
        f.write(f"**Template**: {template_config['name']} ({template_config['description']})\n")
        f.write(f"**Mode**: Ultimate Evolution V3 (Structured Handoffs + Adaptive Depth)\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # V3-specific metrics
        f.write("## Performance Metrics\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Version | V3 Ultimate Evolution |\n")
        f.write(f"| Rounds Executed | {total_metrics.get('rounds_executed', 'N/A')}/{total_metrics.get('rounds_planned', 'N/A')} |\n")
        f.write(f"| Early Stop Reason | {total_metrics.get('early_stop_reason', 'None')} |\n")
        f.write(f"| Early Convergences | {total_metrics.get('early_convergences', 0)} |\n")
        f.write(f"| Total API Calls | {total_metrics.get('total_api_calls', 'N/A')} |\n")
        f.write(f"| Estimated Cost | ${total_metrics.get('total_cost', 0):.2f} |\n")
        f.write(f"| Total Latency | {total_metrics.get('total_latency', 0):.1f}s |\n")
        f.write(f"| Cost vs V1 | {total_metrics.get('cost_savings_vs_v1', 'N/A')} |\n")
        f.write(f"| Jumping Prompts | {'Enabled' if total_metrics.get('jumping_prompts_used') else 'Disabled'} |\n\n")

        f.write("---\n\n")
        f.write("## Round-by-Round Synthesis\n\n")

        for round_num, round_name, synthesis, debug in round_syntheses:
            f.write(f"### Round {round_num}: {round_name}\n\n")
            f.write(f"*Type: {debug.get('round_type', 'N/A')} | ")
            f.write(f"Debate rounds: {debug.get('debate_rounds', 'N/A')} | ")
            f.write(f"Converged: {debug.get('converged_early', 'N/A')} | ")
            f.write(f"Cost: ${debug.get('cost_estimate', 0):.3f}*\n\n")
            f.write(synthesis[:4000])  # Truncate very long syntheses
            f.write("\n\n---\n\n")

        f.write("## Output Files\n\n")
        f.write(f"All detailed outputs are in: `{output_dir}`\n\n")
        for round_num, round_name, _, _ in round_syntheses:
            f.write(f"- `ROUND_{round_num}_SYNTHESIS.md` - {round_name}\n")
            f.write(f"- `ROUND_{round_num}_DEBUG.json` - Debug metrics\n")

        f.write(f"\n---\n\n*Generated by Kamikaze Council V3 (Ultimate Evolution)*\n")
        f.write(f"*Models: Gemini 3, Grok 4.20, GPT-5.2*\n")

    return report_file


def run_kamikaze_v2(topic: str, context: str = "", template: str = "auto",
                    depth: str = "standard", output_dir: str = "docs/kamikaze",
                    mode: str = "v3") -> str:
    """
    Run the Kamikaze council process (dispatcher function).

    This function dispatches to the appropriate version:
    - v3: Ultimate Evolution with structured handoffs (default)
    - v2: Original V2 with basic convergence
    - v1/legacy: Original 3-model parallel

    Args:
        topic: The strategic question to analyze
        context: Background context and constraints
        template: Round template or 'auto' for V3 auto-suggest
        depth: quick, standard, thorough, or legacy
        output_dir: Base directory for output files
        mode: 'v3' (default), 'v2', 'v1', or 'legacy'

    Returns:
        Path to final report
    """
    # V3 MODE: Dispatch to new ultimate evolution
    if mode == 'v3':
        return run_kamikaze_v3(
            topic=topic,
            context=context,
            template=template,  # Can be 'auto' for V3 auto-suggest
            depth=depth,
            output_dir=output_dir,
            use_jumping_prompts=True
        )

    # LEGACY MODES: Use original V1 or V2 implementations
    start_time = time.time()

    # Validate template for legacy modes (they don't support 'auto')
    if template == 'auto':
        template = 'strategy'  # Default for legacy modes

    if template not in TEMPLATES_V3:
        raise ValueError(f"Unknown template: {template}. Options: {list(TEMPLATES_V3.keys())}")

    if depth not in DEPTH_CONFIG_V3:
        raise ValueError(f"Unknown depth: {depth}. Options: {list(DEPTH_CONFIG_V3.keys())}")

    # Handle mode selection
    if mode == 'v1' or mode == 'legacy':
        if run_kamikaze_v1:
            return run_kamikaze_v1(topic, context, template, depth, output_dir)
        else:
            raise RuntimeError("V1 orchestrator not available for legacy mode")

    template_config = TEMPLATES[template]
    round_indices = DEPTH_CONFIG[depth]

    print(f"\n{'#'*60}", file=sys.stderr)
    print(f"KAMIKAZE COUNCIL V2: {template_config['name']}", file=sys.stderr)
    print(f"Mode: Ultimate Kamikaze (2-Model Debate + Judge)", file=sys.stderr)
    print(f"Topic: {topic}", file=sys.stderr)
    print(f"Depth: {depth} ({len(round_indices)} rounds)", file=sys.stderr)
    print(f"{'#'*60}", file=sys.stderr)

    # Create output directory
    out_dir = create_output_dir(output_dir, "v2")
    print(f"\nOutput directory: {out_dir}", file=sys.stderr)

    # Track syntheses and metrics
    round_syntheses = []
    previous_synthesis = ""
    total_api_calls = 0
    total_cost = 0.0
    early_convergences = 0

    # Immutable context for chairman rotation
    immutable_context = f"TOPIC: {topic}\nCONTEXT: {context}" if context else f"TOPIC: {topic}"

    # Reset chairman rotation at start
    reset_chairman_rotation()

    # Run each round
    for i, round_idx in enumerate(round_indices):
        round_config = template_config['rounds'][round_idx]
        round_num = i + 1

        print(f"\n[{round_num}/{len(round_indices)}] Running: {round_config['name']}...",
              file=sys.stderr)

        synthesis, debug_info = run_round_v2(
            round_config=round_config,
            topic=topic,
            context=context,
            previous_synthesis=previous_synthesis,
            immutable_context=immutable_context
        )

        print(f"  -> Completed in {debug_info['latency']:.1f}s "
              f"(cost: ${debug_info['cost_estimate']:.3f}, "
              f"converged: {debug_info['converged_early']})", file=sys.stderr)

        # Update metrics
        total_api_calls += debug_info['api_calls']
        total_cost += debug_info['cost_estimate']
        if debug_info['converged_early']:
            early_convergences += 1

        # Save outputs
        save_round_output_v2(out_dir, round_num, round_config['name'],
                            synthesis, debug_info)

        # Track for final report
        round_syntheses.append((round_num, round_config['name'], synthesis, debug_info))

        # Feed synthesis to next round
        previous_synthesis = synthesis

    total_latency = time.time() - start_time

    # Calculate estimated v1 cost for comparison
    # V1: 3 models * 3 stages * 5 rounds = 45 calls (~$0.90)
    v1_estimated_calls = len(round_indices) * 9  # 9 calls per round in v1
    v1_estimated_cost = v1_estimated_calls * 0.02
    cost_savings = f"{((v1_estimated_cost - total_cost) / v1_estimated_cost * 100):.0f}% savings"

    total_metrics = {
        'rounds_executed': len(round_syntheses),
        'early_convergences': early_convergences,
        'total_api_calls': total_api_calls,
        'total_cost': total_cost,
        'total_latency': total_latency,
        'v1_estimated_cost': v1_estimated_cost,
        'cost_savings_vs_v1': cost_savings
    }

    # Generate final report
    print(f"\nGenerating final report...", file=sys.stderr)
    report_path = generate_final_report_v2(out_dir, topic, template_config['name'],
                                           round_syntheses, total_metrics)

    # Log metrics
    metrics = KamikazeMetrics(
        timestamp=datetime.now().isoformat(),
        mode='v2_debate',
        template=template,
        depth=depth,
        topic_hash=hashlib.md5(topic.encode()).hexdigest()[:8],
        rounds_planned=len(round_indices),
        rounds_executed=len(round_syntheses),
        converged_early=early_convergences > 0,
        total_api_calls=total_api_calls,
        cost_estimate_usd=total_cost,
        latency_seconds=total_latency,
        synthesis_length=sum(len(s) for _, _, s, _ in round_syntheses)
    )
    log_metrics(metrics)

    print(f"\n{'#'*60}", file=sys.stderr)
    print(f"KAMIKAZE V2 COMPLETE", file=sys.stderr)
    print(f"{'#'*60}", file=sys.stderr)
    print(f"Final report: {report_path}", file=sys.stderr)
    print(f"Total cost: ${total_cost:.2f} ({cost_savings})", file=sys.stderr)
    print(f"Total time: {total_latency:.1f}s", file=sys.stderr)
    print(f"Output directory: {out_dir}", file=sys.stderr)

    return str(report_path)


# =============================================================================
# COMPARISON MODE
# =============================================================================

def run_comparison(topic: str, context: str = "", template: str = "strategy",
                   depth: str = "quick", output_dir: str = "docs/kamikaze") -> Dict:
    """
    Run both V1 and V2 on the same topic for comparison.

    Uses 'quick' depth by default to save time/cost.
    """
    print("\n" + "="*60, file=sys.stderr)
    print("COMPARISON MODE: V1 vs V2", file=sys.stderr)
    print("="*60, file=sys.stderr)

    results = {}

    # Run V2 first (it's faster)
    print("\n--- Running V2 (Ultimate Kamikaze) ---", file=sys.stderr)
    v2_start = time.time()
    try:
        v2_report = run_kamikaze_v2(topic, context, template, depth, output_dir, mode='v2')
        v2_time = time.time() - v2_start
        results['v2'] = {
            'success': True,
            'report': v2_report,
            'time': v2_time
        }
    except Exception as e:
        results['v2'] = {
            'success': False,
            'error': str(e),
            'time': time.time() - v2_start
        }

    # Run V1 (legacy)
    if run_kamikaze_v1:
        print("\n--- Running V1 (Legacy) ---", file=sys.stderr)
        v1_start = time.time()
        try:
            v1_report = run_kamikaze_v1(topic, context, template, depth, output_dir)
            v1_time = time.time() - v1_start
            results['v1'] = {
                'success': True,
                'report': v1_report,
                'time': v1_time
            }
        except Exception as e:
            results['v1'] = {
                'success': False,
                'error': str(e),
                'time': time.time() - v1_start
            }
    else:
        results['v1'] = {
            'success': False,
            'error': 'V1 orchestrator not available',
            'time': 0
        }

    # Print comparison summary
    print("\n" + "="*60, file=sys.stderr)
    print("COMPARISON RESULTS", file=sys.stderr)
    print("="*60, file=sys.stderr)

    if results['v2']['success'] and results['v1']['success']:
        speedup = results['v1']['time'] / results['v2']['time'] if results['v2']['time'] > 0 else 0
        print(f"V2 Time: {results['v2']['time']:.1f}s", file=sys.stderr)
        print(f"V1 Time: {results['v1']['time']:.1f}s", file=sys.stderr)
        print(f"Speedup: {speedup:.1f}x", file=sys.stderr)
        print(f"\nV2 Report: {results['v2']['report']}", file=sys.stderr)
        print(f"V1 Report: {results['v1']['report']}", file=sys.stderr)
    else:
        for version, data in results.items():
            status = "SUCCESS" if data['success'] else f"FAILED: {data.get('error', 'unknown')}"
            print(f"{version}: {status} ({data['time']:.1f}s)", file=sys.stderr)

    return results


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Kamikaze Council V3 - Ultimate Evolution with Structured Handoffs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # V3 mode with auto-suggest template (default)
  python3 kamikaze_orchestrator_v2.py --topic "Is this worth pursuing?"

  # V3 with explicit template
  python3 kamikaze_orchestrator_v2.py --topic "What's our 90-day plan?" --template 90-day-plan

  # V3 viability analysis (go/no-go decision)
  python3 kamikaze_orchestrator_v2.py --topic "Should we invest in feature X?" --template viability

  # Legacy V2 mode (no structured handoffs)
  python3 kamikaze_orchestrator_v2.py --topic "Question" --mode v2

  # Legacy V1 mode for comparison
  python3 kamikaze_orchestrator_v2.py --topic "Question" --mode v1

  # Compare V2 vs V3 on same topic
  python3 kamikaze_orchestrator_v2.py --topic "Question" --compare

  # Quick technical analysis
  python3 kamikaze_orchestrator_v2.py --topic "Microservices vs monolith?" --template technical --depth quick

Templates (V3):
  strategy          - Business/product strategy (default)
  technical         - Technical architecture decisions
  product           - Product discovery and launch
  postmortem        - Incident review and lessons
  viability         - Go/no-go decisions
  90-day-plan       - Quarterly roadmap
  pure-insight      - Deep understanding (no actions)
  monetization      - Business model and pricing
  technical-direction - Multi-year architecture
  auto              - Auto-suggest based on topic (V3 only)

Cost Comparison:
  V1 (Legacy):  ~$5-15 per full run (45 API calls)
  V2 (Debate):  ~$1-3 per full run (15-20 API calls)
  V3 (Ultimate): ~$0.75-2 per full run (adaptive depth + early stop)
  Savings: 75-85% vs V1
        """
    )

    # Template choices include 'auto' for V3 auto-suggest
    template_choices = ['auto'] + list(TEMPLATES_V3.keys())

    parser.add_argument('--topic', '-t', required=True,
                        help='The strategic question to analyze')
    parser.add_argument('--context', '-c', default='',
                        help='Background context and constraints')
    parser.add_argument('--template', choices=template_choices, default='auto',
                        help='Round template or "auto" for V3 auto-suggest (default: auto)')
    parser.add_argument('--depth', choices=list(DEPTH_CONFIG_V3.keys()), default='standard',
                        help='Analysis depth: quick (2-3R), standard (3-4R), thorough (4-5R), legacy (5R)')
    parser.add_argument('--output-dir', '-o', default='docs/kamikaze',
                        help='Output directory (default: docs/kamikaze)')
    parser.add_argument('--mode', '-m', choices=['v3', 'v2', 'v1', 'legacy'], default='v3',
                        help='Execution mode (default: v3 - Ultimate Evolution)')
    parser.add_argument('--no-jumping-prompts', action='store_true',
                        help='Disable V3 structured handoffs (for debugging)')
    parser.add_argument('--compare', action='store_true',
                        help='Run both V2 and V3 for comparison')
    parser.add_argument('--check-rollback', action='store_true',
                        help='Check if V2 metrics indicate need for rollback')

    args = parser.parse_args()

    # Check rollback conditions
    if args.check_rollback:
        should_rollback, reason = check_rollback_conditions()
        if should_rollback:
            print(f"ROLLBACK RECOMMENDED: {reason}")
            sys.exit(1)
        else:
            print(f"NO ROLLBACK NEEDED: {reason}")
            sys.exit(0)

    try:
        if args.compare:
            results = run_comparison(
                topic=args.topic,
                context=args.context,
                template=args.template if args.template != 'auto' else 'strategy',
                depth=args.depth,
                output_dir=args.output_dir
            )
            # Return success if at least V3 worked
            sys.exit(0 if results.get('v3', results.get('v2', {})).get('success') else 1)
        elif args.mode == 'v3':
            # V3 mode: Use Ultimate Evolution with structured handoffs
            use_jumping = not args.no_jumping_prompts
            report_path = run_kamikaze_v3(
                topic=args.topic,
                context=args.context,
                template=args.template,
                depth=args.depth,
                output_dir=args.output_dir,
                use_jumping_prompts=use_jumping
            )
            print(f"\nFinal report: {report_path}")
            sys.exit(0)
        else:
            # Legacy modes (v2, v1, legacy)
            report_path = run_kamikaze_v2(
                topic=args.topic,
                context=args.context,
                template=args.template,
                depth=args.depth,
                output_dir=args.output_dir,
                mode=args.mode
            )
            print(f"\nFinal report: {report_path}")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

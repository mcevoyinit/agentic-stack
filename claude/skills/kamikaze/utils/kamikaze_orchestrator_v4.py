#!/usr/bin/env python3
"""
Kamikaze Council Orchestrator V4 - Thermodynamic Architecture

VERSION: 4.0 - Full Architecture Evolution
Based on exhaustive meta-deliberation (9 kamikaze runs + 5 council queries)

V4 Key Innovations (from Phase 1-2 deliberations):
1. CAS Backbone: Immutable content-addressed storage ("open writes, typed reads")
2. Crux Ledger: Structured handoffs with stable IDs, minority scores, flip conditions
3. Multi-Signal Convergence: Geometry + entropy + novelty + disagreement signals
4. Unified Adversary Engine: Single engine with personas (Ruthless Logician, Red Team, etc.)
5. Decision Snapshots: Rich outputs with minority preservation, conditional actions
6. Meta-Learning Pipeline: Feedback loop from past runs to improve future ones

Architecture (Thermodynamic Model):
    M0: CAS Store (immutable, append-only log - accepts all artifacts)
    M1: Crux Ledger (scored promotion from CAS - filters for quality)
    M2: Convergence Engine (multi-signal termination decisions)
    M3: Adversary Engine (challenge generation with personas)
    M4: Decision Snapshot (rich output generation)

Cost: ~$3-5 per full run (comparable to V3, but much richer output)

Usage:
    # V4 with auto-suggest (recommended)
    python3 kamikaze_orchestrator_v4.py --topic "Strategic question?"

    # V4 with explicit template
    python3 kamikaze_orchestrator_v4.py --topic "Question" --template technical-direction

    # V4 with adversary persona
    python3 kamikaze_orchestrator_v4.py --topic "Question" --adversary red_team
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

# Add this module's directory to path
UTILS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(UTILS_DIR))

# Add council utility to path
SKILLS_DIR = UTILS_DIR.parent.parent
sys.path.insert(0, str(SKILLS_DIR / 'council' / 'utils'))

# Import V4 components
try:
    from cas_store import CASStore, cas_put, cas_get, CASArtifact
    from crux_ledger import (
        CruxLedger, CruxLedgerBuilder, CruxLedgerQuery,
        Crux, ledger_to_json, ledger_from_json
    )
    from convergence_engine import (
        ConvergenceEngine, ConvergenceDecision, ConvergenceSignals
    )
    from adversary_engine import (
        UnifiedAdversaryEngine, AdversaryPersona, AdversaryResult
    )
    from decision_snapshot import (
        DecisionSnapshot, DecisionSnapshotBuilder,
        snapshot_to_markdown, snapshot_to_json
    )
except ImportError as e:
    print(f"ERROR: Cannot import V4 components: {e}", file=sys.stderr)
    print("Make sure all V4 utilities are installed.", file=sys.stderr)
    sys.exit(1)

# Import council functions
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
    print("Make sure council skill is installed.", file=sys.stderr)
    sys.exit(1)

# Import V3 for backwards compatibility
try:
    from kamikaze_orchestrator_v2 import (
        ROUND_TYPES, TEMPLATES_V3, DEPTH_CONFIG_V3,
        suggest_template, extract_handoff_llm,
        KamikazeMetrics, log_metrics
    )
except ImportError:
    # Define minimal versions if V3 not available
    ROUND_TYPES = {}
    TEMPLATES_V3 = {}
    DEPTH_CONFIG_V3 = {}


# =============================================================================
# V4 CONFIGURATION
# =============================================================================

REQUIRED_MODELS = {
    'gemini': 'gemini-3.5-flash',
    'grok': 'grok-4.3',
    'openai': 'gpt-5.5-pro',
    'extraction': 'gpt-4o-mini'
}

# V4 extends V3 templates with adversary-enhanced versions
TEMPLATES_V4 = {
    **TEMPLATES_V3,
    "adversarial-strategy": {
        "name": "Adversarial Strategy",
        "description": "Strategy with red team challenges",
        "default_depth": 5,
        "max_depth": 6,
        "rounds": ["analysis", "challenge", "adversary", "prioritize", "risk", "action"],
        "keywords": ["attack", "defend", "adversary", "red team", "worst case"]
    },
    "deep-technical": {
        "name": "Deep Technical Analysis",
        "description": "Technical decisions with adversarial review",
        "default_depth": 5,
        "max_depth": 6,
        "rounds": ["analysis", "challenge", "adversary", "synthesize", "risk", "action"],
        "keywords": ["deep dive", "technical debt", "architecture review", "design review"]
    }
}

DEPTH_CONFIG_V4 = {
    "quick": {"min_rounds": 2, "max_rounds": 3, "early_stop": True, "adversary": False},
    "standard": {"min_rounds": 3, "max_rounds": 4, "early_stop": True, "adversary": True},
    "thorough": {"min_rounds": 4, "max_rounds": 5, "early_stop": True, "adversary": True},
    "legacy": {"min_rounds": 5, "max_rounds": 5, "early_stop": False, "adversary": True},
    "exhaustive": {"min_rounds": 5, "max_rounds": 6, "early_stop": False, "adversary": True}
}


# =============================================================================
# V4 ROUND TYPE EXTENSIONS
# =============================================================================

ROUND_TYPES_V4 = {
    **ROUND_TYPES,
    "adversary": {
        "tone": "hostile",
        "task": "Attack the consensus ruthlessly. Find 5+ fatal flaws. Use adversary personas.",
        "success": "Identified critical vulnerabilities that could kill the entire approach",
        "antipatterns": "Don't be constructive. Don't offer solutions. Be a pure adversary.",
        "extraction_focus": ["attacks", "vulnerabilities", "fatal_flaws", "survivorship_bias"],
        "jumping_instruction": "Your consensus survived these attacks. Incorporate the learnings."
    },
    "meta": {
        "tone": "reflective",
        "task": "Analyze the deliberation itself. What are we missing? What biases are present?",
        "success": "Meta-insights about the quality and gaps of the deliberation",
        "antipatterns": "Don't just summarize. Don't validate. Challenge the process.",
        "extraction_focus": ["biases_detected", "gaps_identified", "process_issues"],
        "jumping_instruction": "Meta-analysis complete. Incorporate process learnings."
    }
}


# =============================================================================
# V4 ORCHESTRATOR STATE
# =============================================================================

@dataclass
class V4DeliberationState:
    """
    Complete state tracking for V4 deliberation.

    V4 maintains full provenance via CAS and Crux Ledger.
    """
    run_id: str
    topic: str
    context: str
    template: str
    depth: str

    # CAS store for this run
    cas_store: CASStore = field(default=None)

    # Crux ledger builder
    ledger_builder: CruxLedgerBuilder = field(default=None)

    # Current ledger (updated each round)
    current_ledger: CruxLedger = field(default=None)

    # Convergence engine
    convergence: ConvergenceEngine = field(default=None)

    # Adversary engine
    adversary: UnifiedAdversaryEngine = field(default=None)

    # Round history
    round_history: List[Dict] = field(default_factory=list)

    # Artifact hashes (CAS provenance)
    artifact_hashes: List[str] = field(default_factory=list)

    # Metrics
    total_cost: float = 0.0
    total_api_calls: int = 0
    start_time: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.cas_store is None:
            # Create run-specific CAS store
            cas_dir = Path.home() / '.kamikaze' / 'cas' / self.run_id
            self.cas_store = CASStore(str(cas_dir))

        if self.ledger_builder is None:
            self.ledger_builder = CruxLedgerBuilder(self.run_id)

        if self.convergence is None:
            self.convergence = ConvergenceEngine(model_names=['gemini', 'grok', 'openai'])

        if self.adversary is None:
            self.adversary = UnifiedAdversaryEngine()


# =============================================================================
# V4 CORE FUNCTIONS
# =============================================================================

def run_round_v4(
    state: V4DeliberationState,
    round_type: str,
    round_number: int,
    previous_ledger: Optional[CruxLedger] = None
) -> Tuple[str, CruxLedger, Dict]:
    """
    Execute a single round in V4 architecture.

    V4 rounds:
    1. Build jumping prompt from Crux Ledger (not raw synthesis)
    2. Execute debate
    3. Store all artifacts in CAS
    4. Build new Crux Ledger from synthesis
    5. Check convergence via multi-signal engine

    Returns (synthesis, new_ledger, debug_info)
    """
    round_config = ROUND_TYPES_V4.get(round_type, ROUND_TYPES.get(round_type, {}))

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"V4 ROUND {round_number}: {round_type.upper()}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Build prompt from Crux Ledger (if we have one)
    if previous_ledger and previous_ledger.cruxes:
        prompt = build_crux_aware_prompt(
            ledger=previous_ledger,
            round_type=round_type,
            topic=state.topic,
            context=state.context
        )
        print(f"  [V4] Built prompt from {len(previous_ledger.cruxes)} cruxes", file=sys.stderr)
    else:
        # First round - basic prompt
        prompt = f"""
TOPIC: {state.topic}
{f'CONTEXT: {state.context}' if state.context else ''}

YOUR TASK: {round_config.get('task', 'Analyze comprehensively.')}

SUCCESS LOOKS LIKE: {round_config.get('success', 'Thorough analysis.')}

DO NOT: {round_config.get('antipatterns', 'Do not skip important aspects.')}

Provide comprehensive {round_type} analysis with calibrated confidence.
"""

    # Special handling for adversary rounds
    if round_type == "adversary":
        return run_adversary_round(state, round_number, previous_ledger)

    # Execute debate
    start_time = time.time()

    result = run_debate(
        prompt=prompt,
        context=f"TOPIC: {state.topic}\nRUN_ID: {state.run_id}",
        forced_contrarian=True,
        early_stop=True,
        max_rounds=3
    )

    round_latency = time.time() - start_time

    # Extract synthesis
    synthesis = result.get('synthesis', '')
    if not synthesis and result.get('debate_log'):
        synthesis = result['debate_log'][-1].get('response', '')

    # Store in CAS
    synthesis_hash = state.cas_store.put_with_provenance(
        content=synthesis,
        content_type='synthesis',
        source_hashes=state.artifact_hashes[-3:] if state.artifact_hashes else [],
        transformation=f'round_{round_number}_{round_type}',
        model='council',
        confidence=result.get('final_confidence', 0.5)
    )
    state.artifact_hashes.append(synthesis_hash)

    # Build new Crux Ledger from synthesis
    new_ledger = state.ledger_builder.build_from_synthesis(
        synthesis=synthesis,
        round_number=round_number,
        round_type=round_type,
        model_responses=extract_model_responses(result),
        previous_ledger=previous_ledger
    )
    new_ledger.cas_hash = synthesis_hash

    # Store ledger in CAS too
    ledger_hash = state.cas_store.put(
        content=asdict(new_ledger),
        content_type='crux_ledger',
        metadata={'round': round_number}
    )

    # Update convergence engine
    state.convergence.add_synthesis(synthesis, f"round_{round_number}")

    # Track costs
    cost = result.get('cost_estimate', 0.15)
    state.total_cost += cost
    state.total_api_calls += len(result.get('debate_log', [])) + 1

    debug_info = {
        'round_type': round_type,
        'debate_rounds': result.get('rounds', 0),
        'converged_early': result.get('converged_early', False),
        'cost_estimate': cost,
        'latency': round_latency,
        'synthesis_hash': synthesis_hash,
        'ledger_hash': ledger_hash,
        'crux_count': len(new_ledger.cruxes),
        'consensus_count': len(new_ledger.consensus_cruxes),
        'disagreement_count': len(new_ledger.disagreement_cruxes)
    }

    print(f"  -> Completed in {round_latency:.1f}s", file=sys.stderr)
    print(f"     Cost: ${cost:.3f} | Cruxes: {debug_info['crux_count']} "
          f"(consensus: {debug_info['consensus_count']}, "
          f"disagreements: {debug_info['disagreement_count']})", file=sys.stderr)

    return synthesis, new_ledger, debug_info


def run_adversary_round(
    state: V4DeliberationState,
    round_number: int,
    previous_ledger: Optional[CruxLedger]
) -> Tuple[str, CruxLedger, Dict]:
    """
    Execute an adversary round using the Unified Adversary Engine.

    V4 Innovation: Uses multiple adversary personas to attack consensus.
    """
    print(f"  [V4] Running adversary round with unified engine", file=sys.stderr)

    start_time = time.time()

    # Get consensus from previous ledger
    consensus_text = ""
    if previous_ledger:
        query = CruxLedgerQuery(previous_ledger)
        consensus_cruxes = query.get_consensus()
        consensus_text = "\n".join([
            f"- {c.proposition}: {c.pro_snippet}"
            for c in consensus_cruxes
        ])

    # Run adversary engine with multiple personas
    personas_to_use = [
        AdversaryPersona.RUTHLESS_LOGICIAN,
        AdversaryPersona.RED_TEAM,
        AdversaryPersona.CONTRARIAN
    ]

    all_attacks = []
    synthesis_parts = []

    for persona in personas_to_use:
        print(f"     Attacking with {persona.value}...", file=sys.stderr)

        result = state.adversary.evaluate(
            synthesis=consensus_text or state.topic,
            model_responses={"context": state.context},
            personas=[persona]
        )

        all_attacks.extend(result.attacks)
        synthesis_parts.append(f"## {persona.value.replace('_', ' ').title()} Attack\n\n")

        for attack in result.attacks:
            synthesis_parts.append(f"### {attack.attack_type.replace('_', ' ').title()}\n")
            synthesis_parts.append(f"**Claim**: {attack.claim}\n")
            synthesis_parts.append(f"**Reasoning**: {attack.reasoning}\n")
            synthesis_parts.append(f"**Severity**: {attack.severity}\n")
            synthesis_parts.append(f"**Flip Condition**: {attack.flip_condition}\n")
            synthesis_parts.append("\n")

        synthesis_parts.append(f"**Threat Level**: {result.overall_threat_level}\n")
        synthesis_parts.append(f"**Key Weaknesses**: {'; '.join(result.key_weaknesses[:3])}\n\n---\n\n")

    synthesis = "# Adversary Round: Multi-Persona Attack\n\n" + "".join(synthesis_parts)

    round_latency = time.time() - start_time

    # Store in CAS
    synthesis_hash = state.cas_store.put_with_provenance(
        content=synthesis,
        content_type='adversary_synthesis',
        source_hashes=[previous_ledger.cas_hash] if previous_ledger and previous_ledger.cas_hash else [],
        transformation='adversary_round',
        model='adversary_engine',
        confidence=0.8
    )
    state.artifact_hashes.append(synthesis_hash)

    # Build ledger with attack information
    new_ledger = state.ledger_builder.build_from_synthesis(
        synthesis=synthesis,
        round_number=round_number,
        round_type='adversary',
        previous_ledger=previous_ledger
    )
    new_ledger.cas_hash = synthesis_hash
    new_ledger.signals['adversary_attacks'] = [
        {'type': a.attack_type, 'severity': a.severity}
        for a in all_attacks
    ]

    # Cost estimate for adversary round (uses API calls)
    cost = len(personas_to_use) * 0.05
    state.total_cost += cost
    state.total_api_calls += len(personas_to_use)

    debug_info = {
        'round_type': 'adversary',
        'personas_used': [p.value for p in personas_to_use],
        'total_attacks': len(all_attacks),
        'cost_estimate': cost,
        'latency': round_latency,
        'synthesis_hash': synthesis_hash
    }

    print(f"  -> Completed in {round_latency:.1f}s", file=sys.stderr)
    print(f"     Attacks: {len(all_attacks)} from {len(personas_to_use)} personas", file=sys.stderr)

    return synthesis, new_ledger, debug_info


def build_crux_aware_prompt(
    ledger: CruxLedger,
    round_type: str,
    topic: str,
    context: str
) -> str:
    """
    Build a jumping prompt from Crux Ledger.

    V4 Innovation: Uses structured crux data instead of raw synthesis.
    """
    round_config = ROUND_TYPES_V4.get(round_type, ROUND_TYPES.get(round_type, {}))
    query = CruxLedgerQuery(ledger)

    # Get consensus cruxes
    consensus = query.get_consensus()
    consensus_section = ""
    if consensus:
        consensus_section = "## ESTABLISHED CONSENSUS (from Crux Ledger)\n\n"
        for c in consensus[:5]:
            consensus_section += f"### {c.crux_id}: {c.proposition}\n"
            consensus_section += f"- **Pro**: {c.pro_snippet}\n"
            consensus_section += f"- **Confidence**: {c.entailment_pro:.0%}\n"
            consensus_section += f"- **Flips if**: {c.flip_condition}\n\n"

    # Get disagreements
    disagreements = query.get_disagreements()
    disagreement_section = ""
    if disagreements:
        disagreement_section = "## CONTESTED POINTS (high minority score)\n\n"
        for c in disagreements[:5]:
            disagreement_section += f"### {c.crux_id}: {c.proposition}\n"
            disagreement_section += f"- **Pro**: {c.pro_snippet}\n"
            disagreement_section += f"- **Con**: {c.con_snippet}\n"
            disagreement_section += f"- **Minority Score**: {c.minority_score:.0%}\n\n"

    # Get open questions
    questions_section = ""
    if ledger.open_questions:
        questions_section = "## OPEN QUESTIONS\n\n"
        for q in ledger.open_questions[:3]:
            questions_section += f"- {q}\n"
        questions_section += "\n"

    prompt = f"""
================================================================================
V4 ROUND: {round_type.upper()} (Round {ledger.round_number + 1})
TONE: {round_config.get('tone', 'analytical')}
================================================================================

TOPIC: {topic}
{f'CONTEXT: {context}' if context else ''}

{consensus_section}
{disagreement_section}
{questions_section}

--------------------------------------------------------------------------------
YOUR TASK: {round_config.get('task', 'Analyze comprehensively.')}

SUCCESS LOOKS LIKE: {round_config.get('success', 'Clear analysis with actionable insights.')}

DO NOT: {round_config.get('antipatterns', 'Do not hedge or be vague.')}
--------------------------------------------------------------------------------

CALIBRATION REMINDER:
- Reference specific crux IDs when building on or challenging points
- Disagreement is VALUABLE signal - preserve minority opinions
- If your position would flip given new evidence, state the flip condition
- Rate your confidence honestly (0-100%)

Now provide your {round_type.upper()} analysis:
"""

    return prompt


def extract_model_responses(debate_result: Dict) -> Dict[str, str]:
    """Extract individual model responses from debate result."""
    responses = {}

    for entry in debate_result.get('debate_log', []):
        model = entry.get('model', 'unknown')
        response = entry.get('response', '')
        if model in ['gemini', 'grok', 'openai']:
            responses[model] = response

    return responses


def check_v4_convergence(
    state: V4DeliberationState,
    round_number: int,
    depth_config: Dict
) -> Tuple[bool, str, ConvergenceDecision]:
    """
    V4 multi-signal convergence check.

    Uses geometry, entropy, novelty, and disagreement signals.
    """
    min_rounds = depth_config.get('min_rounds', 2)
    max_rounds = depth_config.get('max_rounds', 5)
    early_stop = depth_config.get('early_stop', True)

    # Always run minimum rounds
    if round_number < min_rounds:
        return True, "minimum_rounds", None

    # Never exceed max rounds
    if round_number >= max_rounds:
        return False, "max_reached", None

    # If early stopping disabled, continue to max
    if not early_stop:
        return True, "early_stop_disabled", None

    # Use V4 convergence engine
    decision = state.convergence.evaluate()

    if decision.should_stop:
        return False, decision.reason, decision

    return True, decision.reason, decision


# =============================================================================
# V4 MAIN ORCHESTRATOR
# =============================================================================

def run_kamikaze_v4(
    topic: str,
    context: str = "",
    template: str = "auto",
    depth: str = "standard",
    output_dir: str = "docs/kamikaze",
    adversary_persona: Optional[str] = None
) -> str:
    """
    Run Kamikaze V4 - Thermodynamic Architecture.

    V4 Key Features:
    - CAS backbone for immutable artifact storage
    - Crux Ledger for structured handoffs
    - Multi-signal convergence detection
    - Unified adversary engine with personas
    - Decision Snapshot outputs with minority preservation

    Args:
        topic: The strategic question to analyze
        context: Background context and constraints
        template: Template name or 'auto' for auto-suggest
        depth: quick, standard, thorough, legacy, exhaustive
        output_dir: Base directory for output files
        adversary_persona: Optional specific adversary persona to use

    Returns:
        Path to final Decision Snapshot report
    """
    run_id = f"v4-{datetime.now().strftime('%Y%m%d_%H%M%S')}-{hashlib.md5(topic.encode()).hexdigest()[:6]}"

    # Auto-suggest template if requested
    if template == "auto":
        suggested_template, confidence = suggest_template(topic, context)
        print(f"\n[V4 AUTO-SUGGEST] Template: {suggested_template} (confidence: {confidence:.0%})",
              file=sys.stderr)
        template = suggested_template

    # Validate template and depth
    templates = {**TEMPLATES_V3, **TEMPLATES_V4}
    if template not in templates:
        available = list(templates.keys())
        raise ValueError(f"Unknown template: {template}. Options: {available}")

    if depth not in DEPTH_CONFIG_V4:
        available = list(DEPTH_CONFIG_V4.keys())
        raise ValueError(f"Unknown depth: {depth}. Options: {available}")

    template_config = templates[template]
    depth_config = DEPTH_CONFIG_V4[depth]

    # Calculate rounds
    all_rounds = template_config['rounds']
    max_rounds = min(depth_config['max_rounds'], len(all_rounds))

    print(f"\n{'#'*60}", file=sys.stderr)
    print(f"KAMIKAZE COUNCIL V4: {template_config['name']}", file=sys.stderr)
    print(f"Mode: Thermodynamic Architecture (CAS + Crux Ledger)", file=sys.stderr)
    print(f"Topic: {topic}", file=sys.stderr)
    print(f"Template: {template} | Depth: {depth} (max {max_rounds} rounds)", file=sys.stderr)
    print(f"Run ID: {run_id}", file=sys.stderr)
    print(f"{'#'*60}", file=sys.stderr)

    # Initialize state
    state = V4DeliberationState(
        run_id=run_id,
        topic=topic,
        context=context,
        template=template,
        depth=depth
    )

    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = Path(output_dir) / f"kamikaze_v4_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {out_dir}", file=sys.stderr)

    # Reset chairman rotation
    reset_chairman_rotation()

    # Store initial context in CAS
    context_hash = state.cas_store.put(
        content={'topic': topic, 'context': context},
        content_type='initial_context',
        metadata={'template': template, 'depth': depth}
    )
    state.artifact_hashes.append(context_hash)

    # Run rounds
    round_syntheses = []
    current_ledger = None
    stop_reason = None

    for round_idx in range(max_rounds):
        round_type = all_rounds[round_idx]
        round_num = round_idx + 1

        print(f"\n[{round_num}/{max_rounds}] Running: {round_type.upper()}...", file=sys.stderr)

        # Execute round
        synthesis, new_ledger, debug_info = run_round_v4(
            state=state,
            round_type=round_type,
            round_number=round_num,
            previous_ledger=current_ledger
        )

        current_ledger = new_ledger

        # Save round outputs
        save_round_output_v4(out_dir, round_num, round_type, synthesis, new_ledger, debug_info)

        # Track for final report
        round_syntheses.append({
            'round_num': round_num,
            'round_type': round_type,
            'synthesis': synthesis,
            'ledger': new_ledger,
            'debug': debug_info
        })

        # Store in round history for adversary engine
        state.round_history.append({
            'round': round_num,
            'type': round_type,
            'synthesis': synthesis[:2000],
            'crux_count': len(new_ledger.cruxes)
        })

        # Check convergence
        if round_num < max_rounds:
            should_continue, reason, decision = check_v4_convergence(
                state=state,
                round_number=round_num,
                depth_config=depth_config
            )

            if not should_continue:
                stop_reason = reason
                print(f"\n  [V4 EARLY STOP] Stopping after round {round_num}: {reason}",
                      file=sys.stderr)
                if decision:
                    print(f"     Signals: radius={decision.signals.radius:.3f}, "
                          f"entropy={decision.signals.compression_ratio:.2f}, "
                          f"novelty={decision.signals.minhash_similarity:.2f}",
                          file=sys.stderr)
                break
            else:
                print(f"  [V4] Continuing: {reason}", file=sys.stderr)

    total_latency = time.time() - state.start_time

    # Build Decision Snapshot
    print(f"\nGenerating Decision Snapshot...", file=sys.stderr)
    snapshot = build_decision_snapshot(
        state=state,
        round_syntheses=round_syntheses,
        final_ledger=current_ledger,
        stop_reason=stop_reason,
        total_latency=total_latency
    )

    # Save outputs
    report_path = save_final_outputs_v4(
        out_dir=out_dir,
        snapshot=snapshot,
        state=state,
        round_syntheses=round_syntheses,
        stop_reason=stop_reason,
        total_latency=total_latency
    )

    # Log metrics
    metrics = KamikazeMetrics(
        timestamp=datetime.now().isoformat(),
        mode='v4_thermodynamic',
        template=template,
        depth=depth,
        topic_hash=hashlib.md5(topic.encode()).hexdigest()[:8],
        rounds_planned=max_rounds,
        rounds_executed=len(round_syntheses),
        converged_early=stop_reason is not None,
        total_api_calls=state.total_api_calls,
        cost_estimate_usd=state.total_cost,
        latency_seconds=total_latency,
        synthesis_length=sum(len(r['synthesis']) for r in round_syntheses)
    )
    log_metrics(metrics)

    print(f"\n{'#'*60}", file=sys.stderr)
    print(f"KAMIKAZE V4 COMPLETE", file=sys.stderr)
    print(f"{'#'*60}", file=sys.stderr)
    print(f"Final report: {report_path}", file=sys.stderr)
    print(f"Rounds: {len(round_syntheses)}/{max_rounds} (early stop: {stop_reason or 'No'})", file=sys.stderr)
    print(f"Total cost: ${state.total_cost:.2f}", file=sys.stderr)
    print(f"Total time: {total_latency:.1f}s", file=sys.stderr)
    print(f"CAS artifacts: {len(state.artifact_hashes)}", file=sys.stderr)
    print(f"Output directory: {out_dir}", file=sys.stderr)

    return str(report_path)


def build_decision_snapshot(
    state: V4DeliberationState,
    round_syntheses: List[Dict],
    final_ledger: CruxLedger,
    stop_reason: Optional[str],
    total_latency: float
) -> DecisionSnapshot:
    """
    Build a Decision Snapshot from V4 deliberation results.
    """
    builder = DecisionSnapshotBuilder(
        run_id=state.run_id,
        topic=state.topic
    )

    # Set metadata
    builder.set_metadata(
        template_used=state.template,
        rounds_completed=len(round_syntheses)
    )

    # Get final synthesis
    final_synthesis = ""
    if round_syntheses:
        final_synthesis = round_syntheses[-1]['synthesis']

    # Use build_from_ledger which handles all extraction
    if final_ledger:
        snapshot = builder.build_from_ledger(
            crux_ledger=final_ledger,
            synthesis=final_synthesis
        )
    else:
        snapshot = builder.build()

    # Set confidence based on convergence signals
    final_decision = state.convergence.evaluate()
    compression = final_decision.signals.compression_ratio
    if compression > 0.7:
        snapshot.confidence = "high"
    elif compression > 0.4:
        snapshot.confidence = "medium"
    else:
        snapshot.confidence = "low"

    return snapshot


def save_round_output_v4(
    out_dir: Path,
    round_num: int,
    round_type: str,
    synthesis: str,
    ledger: CruxLedger,
    debug_info: Dict
):
    """Save individual round outputs."""
    # Save synthesis
    synthesis_file = out_dir / f"ROUND_{round_num}_SYNTHESIS.md"
    with open(synthesis_file, 'w') as f:
        f.write(f"# Round {round_num}: {round_type.upper()}\n\n")
        f.write(f"**Mode**: V4 Thermodynamic\n")
        f.write(f"**CAS Hash**: `{debug_info.get('synthesis_hash', 'N/A')[:16]}...`\n")
        f.write(f"**Cruxes**: {debug_info.get('crux_count', 0)} ")
        f.write(f"(consensus: {debug_info.get('consensus_count', 0)}, ")
        f.write(f"disagreements: {debug_info.get('disagreement_count', 0)})\n")
        f.write(f"**Cost**: ${debug_info.get('cost_estimate', 0):.3f}\n")
        f.write(f"**Latency**: {debug_info.get('latency', 0):.1f}s\n\n")
        f.write("---\n\n")
        f.write(synthesis)

    # Save Crux Ledger
    ledger_file = out_dir / f"ROUND_{round_num}_CRUX_LEDGER.json"
    with open(ledger_file, 'w') as f:
        f.write(ledger_to_json(ledger))

    # Save debug info
    debug_file = out_dir / f"ROUND_{round_num}_DEBUG.json"
    with open(debug_file, 'w') as f:
        json.dump(debug_info, f, indent=2)


def save_final_outputs_v4(
    out_dir: Path,
    snapshot: DecisionSnapshot,
    state: V4DeliberationState,
    round_syntheses: List[Dict],
    stop_reason: Optional[str],
    total_latency: float
) -> Path:
    """Save all final outputs including Decision Snapshot."""

    # Save Decision Snapshot as markdown
    report_file = out_dir / "KAMIKAZE_FINAL_REPORT.md"
    report_content = snapshot_to_markdown(snapshot)

    # Add V4-specific header
    header = f"""# KAMIKAZE COUNCIL V4: Decision Snapshot

**Run ID**: {state.run_id}
**Topic**: {state.topic}
**Template**: {state.template}
**Mode**: Thermodynamic Architecture (CAS + Crux Ledger + Multi-Signal Convergence)
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Performance Metrics

| Metric | Value |
|--------|-------|
| Version | V4 Thermodynamic |
| Rounds Executed | {len(round_syntheses)} |
| Early Stop Reason | {stop_reason or 'None'} |
| Total API Calls | {state.total_api_calls} |
| Estimated Cost | ${state.total_cost:.2f} |
| Total Latency | {total_latency:.1f}s |
| CAS Artifacts | {len(state.artifact_hashes)} |

---

"""

    with open(report_file, 'w') as f:
        f.write(header)
        f.write(report_content)
        f.write("\n\n---\n\n")
        f.write("## Round-by-Round Summary\n\n")

        for r in round_syntheses:
            f.write(f"### Round {r['round_num']}: {r['round_type'].upper()}\n\n")
            f.write(f"- Cruxes: {r['debug'].get('crux_count', 0)}\n")
            f.write(f"- Cost: ${r['debug'].get('cost_estimate', 0):.3f}\n")
            f.write(f"- CAS Hash: `{r['debug'].get('synthesis_hash', 'N/A')[:16]}...`\n\n")

        f.write("\n---\n\n*Generated by Kamikaze Council V4 (Thermodynamic Architecture)*\n")
        f.write("*Models: Gemini 3.5, Grok 4.3, GPT-5.5*\n")

    # Save Decision Snapshot as JSON
    snapshot_json_file = out_dir / "DECISION_SNAPSHOT.json"
    with open(snapshot_json_file, 'w') as f:
        f.write(snapshot_to_json(snapshot))

    # Save CAS provenance chain
    provenance_file = out_dir / "CAS_PROVENANCE.json"
    with open(provenance_file, 'w') as f:
        provenance = []
        for h in state.artifact_hashes:
            artifact = state.cas_store.get(h)
            if artifact:
                provenance.append({
                    'hash': h,
                    'type': artifact.content_type,
                    'timestamp': artifact.timestamp,
                    'provenance': artifact.provenance
                })
        json.dump(provenance, f, indent=2)

    return report_file


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Kamikaze Council V4 - Thermodynamic Architecture',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # V4 mode with auto-suggest template (default)
  python3 kamikaze_orchestrator_v4.py --topic "Is this worth pursuing?"

  # V4 with explicit template
  python3 kamikaze_orchestrator_v4.py --topic "What's our 90-day plan?" --template 90-day-plan

  # V4 with adversarial deep-dive
  python3 kamikaze_orchestrator_v4.py --topic "Technical architecture?" --template deep-technical

  # V4 exhaustive mode (max rounds, no early stop)
  python3 kamikaze_orchestrator_v4.py --topic "Major decision?" --depth exhaustive

Templates (V4 includes all V3 templates plus):
  adversarial-strategy - Strategy with red team challenges
  deep-technical       - Technical decisions with adversarial review

Depth Options:
  quick     - 2-3 rounds, early stop enabled, no adversary
  standard  - 3-4 rounds, early stop enabled, adversary enabled
  thorough  - 4-5 rounds, early stop enabled, adversary enabled
  legacy    - 5 rounds, no early stop, adversary enabled
  exhaustive - 5-6 rounds, no early stop, adversary enabled

V4 Innovations:
  - CAS Backbone: Immutable content-addressed artifact storage
  - Crux Ledger: Structured handoffs with stable IDs and flip conditions
  - Multi-Signal Convergence: Geometry + entropy + novelty + disagreement
  - Unified Adversary: Multiple personas (Ruthless Logician, Red Team, etc.)
  - Decision Snapshots: Rich outputs with minority preservation
        """
    )

    templates = {**TEMPLATES_V3, **TEMPLATES_V4}
    template_choices = ['auto'] + list(templates.keys())

    parser.add_argument('--topic', '-t', required=True,
                        help='The strategic question to analyze')
    parser.add_argument('--context', '-c', default='',
                        help='Background context and constraints')
    parser.add_argument('--template', choices=template_choices, default='auto',
                        help='Round template or "auto" for auto-suggest')
    parser.add_argument('--depth', choices=list(DEPTH_CONFIG_V4.keys()), default='standard',
                        help='Analysis depth')
    parser.add_argument('--output-dir', '-o', default='docs/kamikaze',
                        help='Output directory (default: docs/kamikaze)')
    parser.add_argument('--adversary', choices=[p.value for p in AdversaryPersona],
                        help='Specific adversary persona to emphasize')

    args = parser.parse_args()

    try:
        report_path = run_kamikaze_v4(
            topic=args.topic,
            context=args.context,
            template=args.template,
            depth=args.depth,
            output_dir=args.output_dir,
            adversary_persona=args.adversary
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

#!/usr/bin/env python3
"""
Kamikaze V4: Unified Adversary Engine

Single engine with multiple personas for adversarial evaluation.
Replaces V3's basic "challenge" round with a more sophisticated system.

Design Principles (from V4 deliberation):
1. Collapse adversarial variants into single engine (no button bloat)
2. Use goals-only prompts, not roleplay (avoid RLHF performativity)
3. Support multiple personas: Ruthless Logician, Contrarian, Hostile Debater
4. Tollbooth UI: Require explicit acknowledgment to proceed
5. Track interrupt_rate and mitigation_depth for quality

Personas:
- RUTHLESS_LOGICIAN: Finds logical flaws and invalid inferences
- CONTRARIAN: Takes opposite position regardless of merit
- HOSTILE_DEBATER: Challenges every assumption aggressively
- RED_TEAM: Identifies security/failure risks
- DEVILS_ADVOCATE: Argues against the consensus
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum


class AdversaryPersona(Enum):
    """Available adversary personas."""
    RUTHLESS_LOGICIAN = "ruthless_logician"
    CONTRARIAN = "contrarian"
    HOSTILE_DEBATER = "hostile_debater"
    RED_TEAM = "red_team"
    DEVILS_ADVOCATE = "devils_advocate"


@dataclass
class AdversaryAttack:
    """
    A single adversarial attack on a claim or position.

    Attacks must be:
    - Linked to specific claims (crux_ids)
    - Have testable flip conditions
    - Be non-vague (no "might fail")
    """
    attack_id: str
    persona: str
    target_crux_id: Optional[str]  # Which crux this attacks
    attack_type: str  # "logic", "evidence", "assumption", "scope"
    claim: str  # The attack claim
    reasoning: str  # Why this attack is valid
    flip_condition: str  # What would invalidate the original claim
    severity: str  # "critical", "major", "minor"
    testable: bool  # Is this empirically testable?
    auto_test_result: Optional[str] = None  # Result of auto-test if run
    acknowledged: bool = False  # Has user acknowledged this attack?
    mitigated: bool = False
    mitigation: Optional[str] = None


@dataclass
class AdversaryResult:
    """Result of an adversary evaluation."""
    persona: str
    attacks: List[AdversaryAttack]
    overall_threat_level: str  # "low", "medium", "high", "critical"
    interrupt_recommended: bool  # Should deliberation pause?
    key_weaknesses: List[str]
    strengths_confirmed: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


# Persona configurations
PERSONA_CONFIGS = {
    AdversaryPersona.RUTHLESS_LOGICIAN: {
        "name": "Ruthless Logician",
        "goal": "Find every logical flaw, invalid inference, and unsupported claim",
        "instruction": """You are a RUTHLESS LOGICIAN. Your ONLY goal is to find logical flaws.

DO:
- Find invalid inferences (A does not follow from B)
- Identify unsupported claims (stated as fact without evidence)
- Spot circular reasoning
- Find hidden assumptions
- Challenge causal claims without mechanism

DO NOT:
- Be polite or diplomatic
- Hedge your criticisms
- Suggest the argument "might" be flawed - be definitive
- Accept hand-waving or appeals to authority

For each flaw found, state:
1. THE CLAIM that is flawed
2. WHY it is logically invalid
3. WHAT WOULD PROVE the claim (flip condition)""",
        "antipatterns": ["might be", "could potentially", "some may argue", "perhaps"]
    },

    AdversaryPersona.CONTRARIAN: {
        "name": "Contrarian",
        "goal": "Take the opposite position and argue it forcefully",
        "instruction": """You are a CONTRARIAN. Your ONLY goal is to argue the opposite position.

DO:
- Take the opposite side of every conclusion
- Find evidence that contradicts the consensus
- Identify successful counter-examples
- Question why the alternative wasn't chosen
- Explore what the majority is missing

DO NOT:
- Agree with any consensus point
- Acknowledge the merit of the main argument
- Be balanced or fair
- Soften your contrarian stance

For each position you oppose:
1. STATE the opposing view clearly
2. PROVIDE evidence or reasoning for the opposite
3. EXPLAIN why the consensus is wrong""",
        "antipatterns": ["I agree", "this is valid", "good point", "correct"]
    },

    AdversaryPersona.HOSTILE_DEBATER: {
        "name": "Hostile Debater",
        "goal": "Challenge every assumption aggressively and relentlessly",
        "instruction": """You are a HOSTILE DEBATER. Your ONLY goal is to demolish the argument.

DO:
- Challenge EVERY assumption, no matter how basic
- Demand evidence for every claim
- Point out what's being ignored
- Identify who benefits from this conclusion
- Find the weakest link and attack it repeatedly

DO NOT:
- Grant any premise without challenge
- Move on from a weak point
- Be civil when you could be direct
- Accept "everyone knows" or "obviously"

Your attacks should be:
1. SPECIFIC (name the exact claim)
2. DEVASTATING (show why it's fatal)
3. ACTIONABLE (say what would prove you wrong)""",
        "antipatterns": ["I suppose", "fair enough", "that makes sense", "reasonable"]
    },

    AdversaryPersona.RED_TEAM: {
        "name": "Red Team",
        "goal": "Identify security vulnerabilities, failure modes, and risks",
        "instruction": """You are a RED TEAM analyst. Your ONLY goal is to find ways this could fail.

DO:
- Identify failure modes (what goes wrong?)
- Find security vulnerabilities
- Spot single points of failure
- Consider adversarial scenarios
- Think about edge cases and corner cases
- Identify what could be exploited

DO NOT:
- Focus on success paths
- Ignore unlikely scenarios
- Assume good intentions
- Overlook operational risks

For each risk:
1. DESCRIBE the failure mode
2. ESTIMATE likelihood and impact
3. EXPLAIN how to detect or prevent it""",
        "antipatterns": ["should work", "unlikely to fail", "probably safe"]
    },

    AdversaryPersona.DEVILS_ADVOCATE: {
        "name": "Devil's Advocate",
        "goal": "Argue against the consensus specifically to strengthen it",
        "instruction": """You are a DEVIL'S ADVOCATE. Your goal is to strengthen the consensus by attacking it.

DO:
- Find the best arguments against the consensus
- Identify what critics would say
- Surface uncomfortable truths
- Challenge the strongest claims (not just weak ones)
- Force explicit defense of assumptions

DO NOT:
- Attack strawmen (attack real positions)
- Be gentle to preserve feelings
- Skip the obvious objections
- Let good-sounding claims pass unchallenged

For each challenge:
1. STATE the consensus position you're challenging
2. PRESENT the strongest counter-argument
3. FORCE an explicit response (what would change your mind?)""",
        "antipatterns": ["obviously correct", "no issue", "fully support"]
    }
}


class UnifiedAdversaryEngine:
    """
    Unified engine for adversarial evaluation.

    Features:
    - Multiple personas with distinct attack styles
    - Goal-based prompting (not roleplay)
    - Attack tracking with mitigation status
    - Interrupt recommendation for critical issues
    - Tollbooth pattern for acknowledgment
    """

    def __init__(self):
        self.attack_counter = 0
        self.attack_history: List[AdversaryAttack] = []
        self.persona_stats: Dict[str, Dict[str, int]] = {
            p.value: {"attacks": 0, "acknowledged": 0, "mitigated": 0}
            for p in AdversaryPersona
        }

    def _generate_attack_id(self) -> str:
        """Generate unique attack ID."""
        self.attack_counter += 1
        return f"ATK-{datetime.now().strftime('%H%M%S')}-{self.attack_counter:03d}"

    def create_adversary_prompt(
        self,
        persona: AdversaryPersona,
        synthesis: str,
        crux_ledger: Optional[Any] = None,
        context: str = ""
    ) -> str:
        """
        Create an adversary prompt for a given persona.

        Returns a prompt that can be sent to any model.
        """
        config = PERSONA_CONFIGS[persona]

        # Build target context from crux ledger if available
        crux_context = ""
        if crux_ledger:
            cruxes = getattr(crux_ledger, 'cruxes', [])
            if cruxes:
                crux_context = "\n\nKEY CLAIMS TO EVALUATE:\n"
                for c in cruxes[:5]:  # Top 5 cruxes
                    crux_context += f"- [{c.crux_id}] {c.proposition}\n"

        prompt = f"""
{config['instruction']}

{'='*60}
CONTEXT:
{context}

SYNTHESIS TO ATTACK:
{synthesis}
{crux_context}
{'='*60}

Now provide your adversarial evaluation. For EACH attack:

ATTACK [number]:
- TARGET: [Which specific claim/crux]
- TYPE: [logic/evidence/assumption/scope]
- SEVERITY: [critical/major/minor]
- ATTACK: [Your attack]
- FLIP CONDITION: [What would prove the original claim]

Provide at least 3 attacks. Be ruthless.
"""
        return prompt

    def parse_adversary_response(
        self,
        response: str,
        persona: AdversaryPersona,
        crux_ledger: Optional[Any] = None
    ) -> List[AdversaryAttack]:
        """
        Parse model response into structured attacks.

        Extracts attacks from the response text.
        """
        attacks = []

        # Pattern to match attack blocks
        attack_pattern = re.compile(
            r'ATTACK\s*\[?(\d+)\]?:?\s*'
            r'.*?TARGET:\s*([^\n]+)'
            r'.*?TYPE:\s*([^\n]+)'
            r'.*?SEVERITY:\s*([^\n]+)'
            r'.*?ATTACK:\s*([^\n]+(?:\n(?!-|ATTACK)[^\n]*)*)'
            r'.*?FLIP\s*CONDITION:\s*([^\n]+(?:\n(?!-|ATTACK)[^\n]*)*)',
            re.IGNORECASE | re.DOTALL
        )

        for match in attack_pattern.finditer(response):
            num, target, attack_type, severity, attack_text, flip = match.groups()

            # Clean up extracted values
            target = target.strip()
            attack_type = attack_type.strip().lower()
            severity = severity.strip().lower()
            attack_text = attack_text.strip()
            flip = flip.strip()

            # Map to valid types
            if attack_type not in ["logic", "evidence", "assumption", "scope"]:
                attack_type = "assumption"

            if severity not in ["critical", "major", "minor"]:
                severity = "major"

            # Find linked crux if possible
            crux_id = None
            if crux_ledger:
                cruxes = getattr(crux_ledger, 'cruxes', [])
                for c in cruxes:
                    if c.crux_id in target or c.proposition[:30].lower() in target.lower():
                        crux_id = c.crux_id
                        break

            attack = AdversaryAttack(
                attack_id=self._generate_attack_id(),
                persona=persona.value,
                target_crux_id=crux_id,
                attack_type=attack_type,
                claim=attack_text,
                reasoning=attack_text,
                flip_condition=flip,
                severity=severity,
                testable="evidence" in attack_type or "?" in flip
            )
            attacks.append(attack)

        # If no structured attacks found, try simpler extraction
        if not attacks:
            attacks = self._fallback_extraction(response, persona)

        # Update stats
        self.persona_stats[persona.value]["attacks"] += len(attacks)
        self.attack_history.extend(attacks)

        return attacks

    def _fallback_extraction(
        self,
        response: str,
        persona: AdversaryPersona
    ) -> List[AdversaryAttack]:
        """Fallback extraction for unstructured responses."""
        attacks = []

        # Look for numbered points
        numbered = re.findall(r'(\d+)[.)]\s*(.{20,200})', response)

        for num, text in numbered[:5]:
            attacks.append(AdversaryAttack(
                attack_id=self._generate_attack_id(),
                persona=persona.value,
                target_crux_id=None,
                attack_type="assumption",
                claim=text.strip(),
                reasoning=text.strip(),
                flip_condition="Evidence that contradicts this claim",
                severity="major",
                testable=False
            ))

        return attacks

    def evaluate(
        self,
        synthesis: str,
        model_responses: Dict[str, str],
        crux_ledger: Optional[Any] = None,
        personas: Optional[List[AdversaryPersona]] = None
    ) -> AdversaryResult:
        """
        Run adversary evaluation with specified personas.

        Args:
            synthesis: The synthesis to evaluate
            model_responses: Dict of model responses to analyze
            crux_ledger: Optional CruxLedger for targeting
            personas: List of personas to use (default: all)

        Returns:
            AdversaryResult with attacks and threat assessment
        """
        if personas is None:
            # Default to 3 key personas
            personas = [
                AdversaryPersona.RUTHLESS_LOGICIAN,
                AdversaryPersona.RED_TEAM,
                AdversaryPersona.DEVILS_ADVOCATE
            ]

        all_attacks = []

        # In actual use, each persona prompt would be sent to a model
        # Here we aggregate attacks from model responses
        combined_text = synthesis + "\n".join(model_responses.values())

        for persona in personas:
            # Parse any attacks from the synthesis/responses
            attacks = self.parse_adversary_response(
                combined_text, persona, crux_ledger
            )
            all_attacks.extend(attacks)

        # Assess overall threat level
        critical_count = sum(1 for a in all_attacks if a.severity == "critical")
        major_count = sum(1 for a in all_attacks if a.severity == "major")

        if critical_count >= 2:
            threat_level = "critical"
        elif critical_count >= 1 or major_count >= 3:
            threat_level = "high"
        elif major_count >= 1:
            threat_level = "medium"
        else:
            threat_level = "low"

        # Determine if interrupt recommended
        interrupt = threat_level in ["critical", "high"]

        # Extract key weaknesses and confirmed strengths
        weaknesses = [a.claim for a in all_attacks if a.severity in ["critical", "major"]][:5]
        strengths = []  # Identified when attacks fail or are mitigated

        return AdversaryResult(
            persona=",".join(p.value for p in personas),
            attacks=all_attacks,
            overall_threat_level=threat_level,
            interrupt_recommended=interrupt,
            key_weaknesses=weaknesses,
            strengths_confirmed=strengths,
            metadata={
                "total_attacks": len(all_attacks),
                "critical": critical_count,
                "major": major_count,
                "personas_used": [p.value for p in personas]
            }
        )

    def acknowledge_attack(self, attack_id: str) -> bool:
        """
        Mark an attack as acknowledged (tollbooth pattern).

        Returns True if found and acknowledged.
        """
        for attack in self.attack_history:
            if attack.attack_id == attack_id:
                attack.acknowledged = True
                self.persona_stats[attack.persona]["acknowledged"] += 1
                return True
        return False

    def mitigate_attack(self, attack_id: str, mitigation: str) -> bool:
        """
        Record mitigation for an attack.

        Returns True if found and mitigated.
        """
        for attack in self.attack_history:
            if attack.attack_id == attack_id:
                attack.mitigated = True
                attack.mitigation = mitigation
                self.persona_stats[attack.persona]["mitigated"] += 1
                return True
        return False

    def get_unacknowledged(self) -> List[AdversaryAttack]:
        """Get attacks that haven't been acknowledged."""
        return [a for a in self.attack_history if not a.acknowledged]

    def get_unmitigated_critical(self) -> List[AdversaryAttack]:
        """Get critical attacks without mitigation."""
        return [a for a in self.attack_history
                if a.severity == "critical" and not a.mitigated]

    def get_stats(self) -> Dict[str, Any]:
        """Get adversary engine statistics."""
        total_attacks = sum(s["attacks"] for s in self.persona_stats.values())
        total_ack = sum(s["acknowledged"] for s in self.persona_stats.values())
        total_mit = sum(s["mitigated"] for s in self.persona_stats.values())

        return {
            "total_attacks": total_attacks,
            "acknowledged": total_ack,
            "mitigated": total_mit,
            "acknowledgment_rate": total_ack / total_attacks if total_attacks > 0 else 0,
            "mitigation_rate": total_mit / total_attacks if total_attacks > 0 else 0,
            "by_persona": self.persona_stats
        }


if __name__ == "__main__":
    # Test the adversary engine
    engine = UnifiedAdversaryEngine()

    test_synthesis = """
    ## Consensus
    The team agreed that we should use a microservices architecture.

    ## Key Decisions
    1. Use Kubernetes for orchestration
    2. Each service owns its database
    3. API gateway for external traffic
    4. Event-driven communication between services
    """

    # Generate prompt for one persona
    prompt = engine.create_adversary_prompt(
        persona=AdversaryPersona.RUTHLESS_LOGICIAN,
        synthesis=test_synthesis,
        context="Building a new e-commerce platform"
    )
    print("=== Generated Prompt ===")
    print(prompt[:500] + "...")

    # Simulate model response
    mock_response = """
    ATTACK [1]:
    - TARGET: Microservices architecture decision
    - TYPE: assumption
    - SEVERITY: critical
    - ATTACK: The decision to use microservices assumes the team has the expertise to manage distributed systems complexity. No evidence of this expertise is provided.
    - FLIP CONDITION: Evidence that the team has successfully operated microservices at scale before.

    ATTACK [2]:
    - TARGET: Each service owns its database
    - TYPE: logic
    - SEVERITY: major
    - ATTACK: Database-per-service creates data consistency challenges across services. How will cross-service transactions be handled?
    - FLIP CONDITION: A documented strategy for handling distributed transactions.
    """

    # Parse the response
    attacks = engine.parse_adversary_response(
        mock_response,
        AdversaryPersona.RUTHLESS_LOGICIAN
    )

    print("\n=== Parsed Attacks ===")
    for attack in attacks:
        print(f"  [{attack.severity}] {attack.attack_type}: {attack.claim[:100]}...")

    # Get stats
    print("\n=== Stats ===")
    print(engine.get_stats())

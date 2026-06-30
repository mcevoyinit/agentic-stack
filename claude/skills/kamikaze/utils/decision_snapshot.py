#!/usr/bin/env python3
"""
Kamikaze V4: Decision Snapshot Output Format

Structured output format that preserves minorities and provides
actionable recommendations for decision-makers.

Design Principles (from V4 deliberation):
1. Above-fold summary (10-20 lines for executives)
2. Disagreement Panel (first-class, not footnotes)
3. Conditional recommendations ("Do X unless Y")
4. Tiered actions (Hard/Soft/Question based on evidence)
5. Fragility markers (what could flip conclusions)
6. Full traceability to Crux IDs

Structure:
- DECISION SNAPSHOT (above-fold, scannable)
- DISAGREEMENT PANEL (minority opinions preserved)
- CONDITIONAL ACTIONS (tiered by evidence strength)
- SUPPORTING EVIDENCE (traces to cruxes)
- FRAGILITY ANALYSIS (what could change)
"""

import json
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime


@dataclass
class MinorityOpinion:
    """
    A preserved minority opinion that dissented from consensus.

    Minorities are first-class citizens in V4 output.
    """
    position: str  # The minority position
    strength: float  # 0-1: How strong is this minority? (model ratio)
    reasoning: str  # Why this minority holds this view
    source_model: Optional[str]  # Which model(s) held this view
    conditions: str  # Under what conditions would this become majority?
    crux_refs: List[str] = field(default_factory=list)  # Related crux IDs


@dataclass
class ConditionalAction:
    """
    An action recommendation with conditions and evidence tier.

    Actions are tiered by evidence strength:
    - HARD: Strong explicit evidence, execute immediately
    - SOFT: Supported but with caveats, proceed with monitoring
    - QUESTION: Speculative, gather more information first
    """
    action: str  # What to do
    tier: str  # "hard", "soft", "question"
    condition: str  # "Do X if Y" or "Do X unless Z"
    evidence_strength: float  # 0-1
    owner: Optional[str]  # Suggested owner
    timeline: Optional[str]  # Suggested timeline
    crux_refs: List[str] = field(default_factory=list)


@dataclass
class FragilityMarker:
    """
    Indicates what could flip a conclusion.

    Used to signal uncertainty and potential pivot points.
    """
    conclusion: str  # The conclusion that could flip
    flip_trigger: str  # What would cause it to flip
    likelihood: str  # "low", "medium", "high"
    impact: str  # "low", "medium", "high"
    monitoring_action: str  # How to detect the flip


@dataclass
class DecisionSnapshot:
    """
    The complete decision output with all V4 enhancements.

    This is the final deliverable from a kamikaze deliberation.
    """
    # Metadata
    topic: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    run_id: str = ""
    template_used: str = ""
    rounds_completed: int = 0

    # Above-fold summary (scannable by executives)
    headline: str = ""  # One-line summary
    recommendation: str = ""  # Primary recommendation with condition
    confidence: str = ""  # "high", "medium", "low"
    key_insight: str = ""  # Most important insight

    # Disagreement Panel (first-class)
    minorities: List[MinorityOpinion] = field(default_factory=list)
    consensus_points: List[str] = field(default_factory=list)
    unresolved_tensions: List[str] = field(default_factory=list)

    # Conditional Actions (tiered)
    hard_actions: List[ConditionalAction] = field(default_factory=list)
    soft_actions: List[ConditionalAction] = field(default_factory=list)
    questions_to_answer: List[ConditionalAction] = field(default_factory=list)

    # Fragility Analysis
    fragility_markers: List[FragilityMarker] = field(default_factory=list)
    risk_summary: str = ""

    # Traceability
    crux_count: int = 0
    evidence_density: float = 0.0  # How much of the output is grounded


class DecisionSnapshotBuilder:
    """
    Builder for creating Decision Snapshots from deliberation outputs.

    Takes raw synthesis, crux ledger, and adversary results to produce
    a structured, actionable decision output.
    """

    def __init__(self, topic: str, run_id: str = ""):
        self.topic = topic
        self.run_id = run_id
        self.snapshot = DecisionSnapshot(topic=topic, run_id=run_id)

    def set_metadata(
        self,
        template_used: str,
        rounds_completed: int
    ) -> "DecisionSnapshotBuilder":
        """Set deliberation metadata."""
        self.snapshot.template_used = template_used
        self.snapshot.rounds_completed = rounds_completed
        return self

    def set_headline(
        self,
        headline: str,
        recommendation: str,
        confidence: str,
        key_insight: str
    ) -> "DecisionSnapshotBuilder":
        """Set the above-fold summary."""
        self.snapshot.headline = headline
        self.snapshot.recommendation = recommendation
        self.snapshot.confidence = confidence
        self.snapshot.key_insight = key_insight
        return self

    def add_minority(
        self,
        position: str,
        strength: float,
        reasoning: str,
        source_model: Optional[str] = None,
        conditions: str = "",
        crux_refs: Optional[List[str]] = None
    ) -> "DecisionSnapshotBuilder":
        """Add a minority opinion."""
        self.snapshot.minorities.append(MinorityOpinion(
            position=position,
            strength=strength,
            reasoning=reasoning,
            source_model=source_model,
            conditions=conditions,
            crux_refs=crux_refs or []
        ))
        return self

    def add_consensus(self, point: str) -> "DecisionSnapshotBuilder":
        """Add a consensus point."""
        self.snapshot.consensus_points.append(point)
        return self

    def add_tension(self, tension: str) -> "DecisionSnapshotBuilder":
        """Add an unresolved tension."""
        self.snapshot.unresolved_tensions.append(tension)
        return self

    def add_action(
        self,
        action: str,
        tier: str,
        condition: str,
        evidence_strength: float,
        owner: Optional[str] = None,
        timeline: Optional[str] = None,
        crux_refs: Optional[List[str]] = None
    ) -> "DecisionSnapshotBuilder":
        """Add a conditional action."""
        action_obj = ConditionalAction(
            action=action,
            tier=tier,
            condition=condition,
            evidence_strength=evidence_strength,
            owner=owner,
            timeline=timeline,
            crux_refs=crux_refs or []
        )

        if tier == "hard":
            self.snapshot.hard_actions.append(action_obj)
        elif tier == "soft":
            self.snapshot.soft_actions.append(action_obj)
        else:  # question
            self.snapshot.questions_to_answer.append(action_obj)

        return self

    def add_fragility(
        self,
        conclusion: str,
        flip_trigger: str,
        likelihood: str = "medium",
        impact: str = "medium",
        monitoring_action: str = ""
    ) -> "DecisionSnapshotBuilder":
        """Add a fragility marker."""
        self.snapshot.fragility_markers.append(FragilityMarker(
            conclusion=conclusion,
            flip_trigger=flip_trigger,
            likelihood=likelihood,
            impact=impact,
            monitoring_action=monitoring_action
        ))
        return self

    def set_risk_summary(self, summary: str) -> "DecisionSnapshotBuilder":
        """Set overall risk summary."""
        self.snapshot.risk_summary = summary
        return self

    def set_traceability(
        self,
        crux_count: int,
        evidence_density: float
    ) -> "DecisionSnapshotBuilder":
        """Set traceability metrics."""
        self.snapshot.crux_count = crux_count
        self.snapshot.evidence_density = evidence_density
        return self

    def build(self) -> DecisionSnapshot:
        """Build and return the decision snapshot."""
        return self.snapshot

    def build_from_ledger(
        self,
        crux_ledger: Any,
        synthesis: str,
        adversary_result: Optional[Any] = None
    ) -> DecisionSnapshot:
        """
        Build decision snapshot from a Crux Ledger and synthesis.

        This is the main integration point that combines all V4 components.
        """
        # Extract consensus from ledger
        cruxes = getattr(crux_ledger, 'cruxes', [])

        for crux in cruxes:
            if crux.minority_score < 0.3:
                self.add_consensus(crux.proposition)
            elif crux.minority_score > 0.5:
                self.add_minority(
                    position=crux.proposition,
                    strength=crux.minority_score,
                    reasoning=f"Pro: {crux.pro_snippet[:100]}... Con: {crux.con_snippet[:100]}...",
                    conditions=crux.flip_condition,
                    crux_refs=[crux.crux_id]
                )
            else:
                self.add_tension(crux.proposition)

        # Extract actions from synthesis (heuristic)
        self._extract_actions_from_synthesis(synthesis)

        # Add adversary insights if available
        if adversary_result:
            for attack in getattr(adversary_result, 'attacks', []):
                if attack.severity == "critical":
                    self.add_fragility(
                        conclusion=attack.target_crux_id or "General conclusion",
                        flip_trigger=attack.flip_condition,
                        likelihood="high",
                        impact="high",
                        monitoring_action=f"Address: {attack.claim[:100]}"
                    )

        # Generate headline from synthesis
        self._generate_headline(synthesis)

        # Set traceability
        self.set_traceability(
            crux_count=len(cruxes),
            evidence_density=self._compute_evidence_density(cruxes)
        )

        return self.build()

    def _extract_actions_from_synthesis(self, synthesis: str):
        """Extract action items from synthesis text."""
        import re

        # Look for action patterns
        action_patterns = [
            (r'(?:should|must|need to)\s+([^.!?]+)', "soft"),
            (r'(?:immediately|urgently)\s+([^.!?]+)', "hard"),
            (r'(?:consider|explore|investigate)\s+([^.!?]+)', "question"),
        ]

        for pattern, tier in action_patterns:
            matches = re.findall(pattern, synthesis, re.IGNORECASE)
            for match in matches[:3]:  # Limit per pattern
                self.add_action(
                    action=match.strip(),
                    tier=tier,
                    condition="Based on deliberation consensus",
                    evidence_strength=0.6 if tier == "soft" else (0.8 if tier == "hard" else 0.4)
                )

    def _generate_headline(self, synthesis: str):
        """Generate headline from synthesis."""
        # Take first substantial sentence
        sentences = synthesis.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 150:
                self.snapshot.headline = sentence
                break

        if not self.snapshot.headline:
            self.snapshot.headline = f"Analysis of: {self.topic[:50]}"

        # Generate confidence based on consensus ratio
        consensus_ratio = len(self.snapshot.consensus_points) / max(
            len(self.snapshot.consensus_points) + len(self.snapshot.minorities) + len(self.snapshot.unresolved_tensions),
            1
        )

        if consensus_ratio > 0.7:
            self.snapshot.confidence = "high"
        elif consensus_ratio > 0.4:
            self.snapshot.confidence = "medium"
        else:
            self.snapshot.confidence = "low"

    def _compute_evidence_density(self, cruxes) -> float:
        """Compute how much of the output is grounded in evidence."""
        if not cruxes:
            return 0.0

        grounded = sum(
            1 for c in cruxes
            if c.pro_snippet and len(c.pro_snippet) > 20
        )

        return grounded / len(cruxes)


def snapshot_to_markdown(snapshot: DecisionSnapshot) -> str:
    """Convert decision snapshot to markdown format."""
    md = []

    # Header
    md.append(f"# Decision Snapshot: {snapshot.topic}")
    md.append(f"\n*Generated: {snapshot.generated_at}*")
    md.append(f"*Run ID: {snapshot.run_id}*")
    md.append(f"*Template: {snapshot.template_used}*")
    md.append(f"*Rounds: {snapshot.rounds_completed}*\n")

    # Above-fold Summary
    md.append("---")
    md.append("## Executive Summary")
    md.append(f"\n**{snapshot.headline}**\n")
    md.append(f"**Recommendation:** {snapshot.recommendation}")
    md.append(f"**Confidence:** {snapshot.confidence.upper()}")
    md.append(f"**Key Insight:** {snapshot.key_insight}\n")

    # Disagreement Panel
    md.append("---")
    md.append("## Disagreement Panel")
    md.append("\n*Minority opinions are preserved as first-class citizens*\n")

    if snapshot.minorities:
        for i, minority in enumerate(snapshot.minorities, 1):
            md.append(f"### Minority #{i} (Strength: {minority.strength:.0%})")
            md.append(f"**Position:** {minority.position}")
            md.append(f"**Reasoning:** {minority.reasoning}")
            md.append(f"**Would become majority if:** {minority.conditions}")
            if minority.source_model:
                md.append(f"*Source: {minority.source_model}*")
            md.append("")
    else:
        md.append("*No significant minority opinions recorded*\n")

    # Consensus Points
    if snapshot.consensus_points:
        md.append("### Consensus Points")
        for point in snapshot.consensus_points:
            md.append(f"- {point}")
        md.append("")

    # Unresolved Tensions
    if snapshot.unresolved_tensions:
        md.append("### Unresolved Tensions")
        for tension in snapshot.unresolved_tensions:
            md.append(f"- {tension}")
        md.append("")

    # Actions
    md.append("---")
    md.append("## Conditional Actions")
    md.append("\n*Actions are tiered by evidence strength*\n")

    if snapshot.hard_actions:
        md.append("### HARD Actions (Strong Evidence - Execute)")
        for action in snapshot.hard_actions:
            md.append(f"- **{action.action}**")
            md.append(f"  - Condition: {action.condition}")
            md.append(f"  - Evidence: {action.evidence_strength:.0%}")
            if action.owner:
                md.append(f"  - Owner: {action.owner}")
            if action.timeline:
                md.append(f"  - Timeline: {action.timeline}")
        md.append("")

    if snapshot.soft_actions:
        md.append("### SOFT Actions (Supported - Proceed with Monitoring)")
        for action in snapshot.soft_actions:
            md.append(f"- **{action.action}**")
            md.append(f"  - Condition: {action.condition}")
            md.append(f"  - Evidence: {action.evidence_strength:.0%}")
        md.append("")

    if snapshot.questions_to_answer:
        md.append("### QUESTIONS (Speculative - Gather More Information)")
        for action in snapshot.questions_to_answer:
            md.append(f"- **{action.action}**")
            md.append(f"  - Condition: {action.condition}")
        md.append("")

    # Fragility Analysis
    if snapshot.fragility_markers:
        md.append("---")
        md.append("## Fragility Analysis")
        md.append("\n*What could flip these conclusions?*\n")

        for marker in snapshot.fragility_markers:
            md.append(f"### {marker.conclusion}")
            md.append(f"- **Flips if:** {marker.flip_trigger}")
            md.append(f"- **Likelihood:** {marker.likelihood}")
            md.append(f"- **Impact:** {marker.impact}")
            if marker.monitoring_action:
                md.append(f"- **Monitor:** {marker.monitoring_action}")
            md.append("")

    if snapshot.risk_summary:
        md.append(f"**Overall Risk:** {snapshot.risk_summary}\n")

    # Traceability
    md.append("---")
    md.append("## Traceability")
    md.append(f"\n- Cruxes analyzed: {snapshot.crux_count}")
    md.append(f"- Evidence density: {snapshot.evidence_density:.0%}")

    return "\n".join(md)


def snapshot_to_json(snapshot: DecisionSnapshot) -> str:
    """Convert decision snapshot to JSON."""
    return json.dumps(asdict(snapshot), indent=2)


if __name__ == "__main__":
    # Test the Decision Snapshot system
    builder = DecisionSnapshotBuilder(
        topic="Should we adopt microservices architecture?",
        run_id="test-run-001"
    )

    snapshot = (builder
        .set_metadata(template_used="technical", rounds_completed=4)
        .set_headline(
            headline="Microservices recommended with careful migration",
            recommendation="Adopt microservices, but start with modular monolith",
            confidence="medium",
            key_insight="Team maturity is the key constraint"
        )
        .add_consensus("Domain-driven design is essential")
        .add_consensus("Service boundaries should follow team boundaries")
        .add_minority(
            position="Monolith is sufficient for current scale",
            strength=0.4,
            reasoning="Operational complexity of microservices outweighs benefits at current team size",
            source_model="grok",
            conditions="Team size grows to 20+ engineers"
        )
        .add_tension("Unclear how to handle cross-service transactions")
        .add_action(
            action="Implement modular monolith with clear boundaries",
            tier="hard",
            condition="Immediately",
            evidence_strength=0.85
        )
        .add_action(
            action="Define service extraction criteria",
            tier="soft",
            condition="After modular monolith is stable",
            evidence_strength=0.7
        )
        .add_action(
            action="Evaluate service mesh options",
            tier="question",
            condition="When first service is extracted",
            evidence_strength=0.4
        )
        .add_fragility(
            conclusion="Microservices recommendation",
            flip_trigger="Team loses key distributed systems expertise",
            likelihood="medium",
            impact="high",
            monitoring_action="Track team composition changes"
        )
        .set_risk_summary("Medium risk - dependent on team capabilities")
        .set_traceability(crux_count=12, evidence_density=0.75)
        .build()
    )

    print("=== Decision Snapshot (Markdown) ===")
    print(snapshot_to_markdown(snapshot))

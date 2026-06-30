#!/usr/bin/env python3
"""
Kamikaze V4: Crux Ledger - Structured Handoff System

The Crux Ledger is the "contract" between rounds in V4 deliberation.
It replaces V3's flat JSON extraction with a richer, self-contained format.

Design Principles (from V4 deliberation):
1. Self-contained: Embedded verbatim snippets (≤40 words), not pointers
2. Stable IDs: `C-YYYY-MM-DD-NNN` format for cross-round references
3. Minority preservation: Explicit minority_score for disagreeing views
4. Flip conditions: "What would change my mind?" for each crux
5. Entailment scores: NLI-derived confidence for pro/con arguments
6. Lifecycle: Support for merge, decay, and resolution marking

The Crux Ledger is:
- Sole handoff truth between rounds
- Queryable for downstream engines (convergence, adversary, snapshots)
- Provenance-tracked via CAS integration
"""

import json
import re
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class Crux:
    """
    A single crux (key point of agreement or disagreement).

    A crux is a load-bearing claim that:
    - Has clear pro/con positions
    - Would flip conclusions if disproven
    - Can be traced to evidence
    """
    crux_id: str  # Format: C-YYYY-MM-DD-NNN
    topic_tag: str  # Categorical tag for grouping
    proposition: str  # The claim itself
    pro_snippet: str  # Verbatim supporting quote (≤40 words)
    con_snippet: str  # Verbatim opposing quote (≤40 words)
    minority_score: float  # 0-1: How many models disagreed? (0=consensus, 1=split)
    flip_condition: str  # "Flips if..." - what would change the conclusion
    entailment_pro: float  # 0-1: NLI score for pro argument
    entailment_con: float  # 0-1: NLI score for con argument
    status: str = "active"  # active, merged, resolved, stale
    source_hashes: List[str] = field(default_factory=list)  # CAS provenance
    round_created: int = 0
    last_touched: int = 0
    confidence: float = 0.5  # Overall confidence in this crux


@dataclass
class CruxLedger:
    """
    The complete handoff artifact between rounds.

    Contains:
    - Round metadata
    - Consensus points (cruxes with high agreement)
    - Disagreements (cruxes with high minority_score)
    - Open questions for next round
    - Signals for convergence engine
    """
    ledger_version: str = "1.0"
    run_id: str = ""
    round_number: int = 0
    round_type: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Core crux data
    cruxes: List[Crux] = field(default_factory=list)

    # Categorized views (derived from cruxes)
    consensus_cruxes: List[str] = field(default_factory=list)  # crux_ids
    disagreement_cruxes: List[str] = field(default_factory=list)  # crux_ids
    open_questions: List[str] = field(default_factory=list)

    # Signals for downstream engines
    signals: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    cas_hash: Optional[str] = None  # Hash in CAS store


class CruxLedgerBuilder:
    """
    Builder for creating Crux Ledgers from synthesis text.

    Handles:
    1. Crux ID generation
    2. Snippet extraction and truncation
    3. NLI scoring (via model calls)
    4. Minority score calculation
    5. Lifecycle management
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.crux_counter = 0
        self.date_prefix = datetime.now().strftime("%Y-%m-%d")

    def _generate_crux_id(self) -> str:
        """Generate unique crux ID."""
        self.crux_counter += 1
        return f"C-{self.date_prefix}-{self.crux_counter:03d}"

    def _truncate_snippet(self, text: str, max_words: int = 40) -> str:
        """Truncate snippet to max words while preserving meaning."""
        words = text.split()
        if len(words) <= max_words:
            return text

        truncated = ' '.join(words[:max_words])
        return truncated + "..."

    def _extract_snippets(self, synthesis: str) -> List[Tuple[str, str, str]]:
        """
        Extract (topic, pro_snippet, con_snippet) tuples from synthesis.

        Uses heuristic patterns to find agreements/disagreements.
        Returns list of potential crux foundations.
        """
        snippets = []

        # Pattern 1: "On X, models agree/disagree..."
        pattern1 = re.findall(
            r'(?:on|regarding|about)\s+([^,.:]+)[,:\s]+(?:models?|debaters?)\s+'
            r'(?:agree|consensus|aligned).*?[.!](.{20,200}?)(?:[.!]|$)',
            synthesis, re.IGNORECASE | re.DOTALL
        )
        for topic, snippet in pattern1:
            snippets.append((topic.strip(), self._truncate_snippet(snippet), ""))

        # Pattern 2: Table rows (common in V3 output)
        table_pattern = re.findall(
            r'\|\s*\*?\*?([^|]+)\*?\*?\s*\|\s*([^|]+)\|\s*([^|]+)\|',
            synthesis
        )
        for row in table_pattern:
            if len(row) >= 3 and len(row[0]) > 5:
                topic = row[0].strip()
                pro = self._truncate_snippet(row[1].strip())
                con = self._truncate_snippet(row[2].strip()) if len(row) > 2 else ""
                if not any(t[0] == topic for t in snippets):
                    snippets.append((topic, pro, con))

        # Pattern 3: Bullet points with "however", "but", "disagree"
        bullets = re.findall(
            r'[-*]\s+([^-*\n]+?)(?:however|but|disagree|contest)[^-*\n]+',
            synthesis, re.IGNORECASE
        )
        for bullet in bullets:
            snippets.append((
                self._truncate_snippet(bullet, 10),
                self._truncate_snippet(bullet),
                ""
            ))

        return snippets[:10]  # Limit to top 10 potential cruxes

    def build_from_synthesis(
        self,
        synthesis: str,
        round_number: int,
        round_type: str,
        model_responses: Optional[Dict[str, str]] = None,
        previous_ledger: Optional[CruxLedger] = None
    ) -> CruxLedger:
        """
        Build a Crux Ledger from synthesis text and optional model responses.

        Args:
            synthesis: The synthesis text from the round
            round_number: Current round number
            round_type: Type of round (analysis, challenge, etc.)
            model_responses: Dict of model_name -> response for minority scoring
            previous_ledger: Previous round's ledger for continuity

        Returns:
            CruxLedger: The structured handoff
        """
        ledger = CruxLedger(
            run_id=self.run_id,
            round_number=round_number,
            round_type=round_type,
            metadata={"synthesis_length": len(synthesis)}
        )

        # Extract potential cruxes from synthesis
        snippets = self._extract_snippets(synthesis)

        for topic, pro, con in snippets:
            crux = Crux(
                crux_id=self._generate_crux_id(),
                topic_tag=self._categorize_topic(topic),
                proposition=topic,
                pro_snippet=pro,
                con_snippet=con or "No explicit counter-argument found",
                minority_score=self._calculate_minority_score(topic, model_responses),
                flip_condition=f"Flips if evidence shows {topic} is false",
                entailment_pro=0.7,  # Default; override with NLI
                entailment_con=0.3,  # Default; override with NLI
                round_created=round_number,
                last_touched=round_number
            )
            ledger.cruxes.append(crux)

        # Categorize cruxes
        for crux in ledger.cruxes:
            if crux.minority_score < 0.3:
                ledger.consensus_cruxes.append(crux.crux_id)
            elif crux.minority_score > 0.5:
                ledger.disagreement_cruxes.append(crux.crux_id)

        # Extract open questions
        ledger.open_questions = self._extract_questions(synthesis)

        # Carry forward unresolved cruxes from previous ledger
        if previous_ledger:
            ledger = self._merge_previous(ledger, previous_ledger, round_number)

        return ledger

    def _categorize_topic(self, topic: str) -> str:
        """Assign a categorical tag to a topic."""
        topic_lower = topic.lower()

        categories = {
            "architecture": ["architecture", "design", "system", "structure", "component"],
            "risk": ["risk", "danger", "threat", "failure", "vulnerability"],
            "cost": ["cost", "price", "budget", "expense", "investment"],
            "timeline": ["time", "schedule", "deadline", "milestone", "duration"],
            "technical": ["technical", "implementation", "code", "algorithm", "api"],
            "strategy": ["strategy", "approach", "plan", "direction", "decision"],
            "team": ["team", "people", "hire", "resource", "capacity"],
            "market": ["market", "customer", "user", "demand", "competition"]
        }

        for category, keywords in categories.items():
            if any(kw in topic_lower for kw in keywords):
                return category

        return "general"

    def _calculate_minority_score(
        self,
        topic: str,
        model_responses: Optional[Dict[str, str]]
    ) -> float:
        """
        Calculate minority score based on model response similarity.

        Returns 0 if all agree, higher values indicate disagreement.
        """
        if not model_responses or len(model_responses) < 2:
            return 0.3  # Default when we can't calculate

        topic_lower = topic.lower()
        agreements = 0
        total = len(model_responses)

        for response in model_responses.values():
            response_lower = response.lower()
            # Simple heuristic: topic mentioned positively
            if topic_lower in response_lower:
                if not any(neg in response_lower for neg in ['not ', 'don\'t', 'disagree', 'however']):
                    agreements += 1

        # Return minority ratio (0 = full consensus, 1 = no agreement)
        return 1.0 - (agreements / total) if total > 0 else 0.5

    def _extract_questions(self, synthesis: str) -> List[str]:
        """Extract open questions from synthesis."""
        questions = []

        # Find explicit questions
        question_matches = re.findall(r'([^.!?\n]+\?)', synthesis)
        for q in question_matches[:5]:
            q = q.strip()
            if len(q) > 10 and len(q) < 200:
                questions.append(q)

        # Find "needs to be answered" patterns
        needs_patterns = re.findall(
            r'(?:need(?:s)?|must|should)\s+(?:to\s+)?(?:answer|address|resolve|determine)\s+([^.!?]+)',
            synthesis, re.IGNORECASE
        )
        for need in needs_patterns[:3]:
            questions.append(f"How to {need.strip()}?")

        return questions[:5]

    def _merge_previous(
        self,
        current: CruxLedger,
        previous: CruxLedger,
        round_number: int
    ) -> CruxLedger:
        """
        Merge unresolved cruxes from previous ledger.

        Lifecycle rules:
        - Active cruxes carry forward with touch update
        - Cruxes addressed in current round get merged/resolved
        - Stale cruxes (untouched for 2+ rounds) get marked
        """
        existing_topics = {c.proposition.lower() for c in current.cruxes}

        for prev_crux in previous.cruxes:
            if prev_crux.status != "active":
                continue

            # Check if addressed in current round
            if prev_crux.proposition.lower() in existing_topics:
                continue  # Already represented

            # Check for staleness
            if round_number - prev_crux.last_touched > 2:
                prev_crux.status = "stale"
            else:
                prev_crux.last_touched = round_number

            # Carry forward
            current.cruxes.append(prev_crux)

        return current


class CruxLedgerQuery:
    """
    Query interface for Crux Ledgers.

    Supports typed reads for downstream engines.
    """

    def __init__(self, ledger: CruxLedger):
        self.ledger = ledger
        self._crux_map = {c.crux_id: c for c in ledger.cruxes}

    def get_crux(self, crux_id: str) -> Optional[Crux]:
        """Get a crux by ID."""
        return self._crux_map.get(crux_id)

    def get_consensus(self) -> List[Crux]:
        """Get all consensus cruxes."""
        return [self._crux_map[cid] for cid in self.ledger.consensus_cruxes
                if cid in self._crux_map]

    def get_disagreements(self) -> List[Crux]:
        """Get all disagreement cruxes."""
        return [self._crux_map[cid] for cid in self.ledger.disagreement_cruxes
                if cid in self._crux_map]

    def get_by_tag(self, tag: str) -> List[Crux]:
        """Get cruxes by topic tag."""
        return [c for c in self.ledger.cruxes if c.topic_tag == tag]

    def get_active(self) -> List[Crux]:
        """Get all active (non-stale, non-resolved) cruxes."""
        return [c for c in self.ledger.cruxes if c.status == "active"]

    def get_high_confidence(self, threshold: float = 0.7) -> List[Crux]:
        """Get cruxes with high entailment confidence."""
        return [c for c in self.ledger.cruxes
                if max(c.entailment_pro, c.entailment_con) >= threshold]

    def summarize(self) -> Dict[str, Any]:
        """Get a summary of the ledger."""
        return {
            "total_cruxes": len(self.ledger.cruxes),
            "consensus_count": len(self.ledger.consensus_cruxes),
            "disagreement_count": len(self.ledger.disagreement_cruxes),
            "open_questions": len(self.ledger.open_questions),
            "active_cruxes": len(self.get_active()),
            "by_tag": {tag: len(self.get_by_tag(tag))
                       for tag in set(c.topic_tag for c in self.ledger.cruxes)}
        }


def ledger_to_json(ledger: CruxLedger) -> str:
    """Serialize ledger to JSON."""
    return json.dumps(asdict(ledger), indent=2)


def ledger_from_json(json_str: str) -> CruxLedger:
    """Deserialize ledger from JSON."""
    data = json.loads(json_str)

    # Reconstruct Crux objects
    cruxes = [Crux(**c) for c in data.pop("cruxes", [])]
    ledger = CruxLedger(**data)
    ledger.cruxes = cruxes

    return ledger


if __name__ == "__main__":
    # Test the Crux Ledger system
    test_synthesis = """
    ## CONSENSUS
    Both debaters agree that CAS backbone is essential for V4.
    The architecture should use content-addressed storage.

    ## DISAGREEMENTS
    | Disagreement | OpenAI Position | Gemini Position |
    |--------------|-----------------|-----------------|
    | Schema timing | Early schema required | Flexible-first approach |
    | Migration path | Full ETL needed | Shim layer sufficient |

    Questions that need to be answered:
    - How do we handle backward compatibility?
    - What's the performance impact of CAS lookups?
    """

    builder = CruxLedgerBuilder(run_id="test-run-001")
    ledger = builder.build_from_synthesis(
        synthesis=test_synthesis,
        round_number=1,
        round_type="analysis"
    )

    print("=== Crux Ledger ===")
    print(f"Cruxes: {len(ledger.cruxes)}")
    print(f"Consensus: {ledger.consensus_cruxes}")
    print(f"Disagreements: {ledger.disagreement_cruxes}")
    print(f"Questions: {ledger.open_questions}")

    query = CruxLedgerQuery(ledger)
    print(f"\nSummary: {query.summarize()}")

    print(f"\n=== JSON ===")
    print(ledger_to_json(ledger)[:1000] + "...")

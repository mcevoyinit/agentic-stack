#!/usr/bin/env python3
"""
Kamikaze V4: Convergence Engine v2 - Multi-Signal Detection

Replaces V3's simple similarity thresholds with a sophisticated
multi-signal approach that detects:
- Genuine consensus vs. echo chambers
- Valuable disagreement vs. noise
- Saturation vs. productive iteration

Design Principles (from V4 deliberation):
1. Drop 1B validator - "dumber judge" paradox
2. Use topology/geometry signals (centroid, radius, velocity)
3. Use entropy/compression for echo detection
4. Track novelty via MinHash/SimHash
5. Decouple generation from extraction

Signal Types:
- Geometry: Embedding space analysis (radius, velocity, cluster count)
- Entropy: Information density and saturation
- Novelty: New claims vs. repeated content
- Disagreement: Explicit conflict tracking
"""

import math
import hashlib
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter


@dataclass
class ConvergenceDecision:
    """
    Decision output from convergence analysis.

    Provides a simplified interface for the orchestrator.
    """
    should_stop: bool
    reason: str
    signals: 'ConvergenceSignals'
    confidence: float = 0.5


@dataclass
class ConvergenceSignals:
    """
    Multi-signal convergence state for a round.

    Contains all signals needed to decide:
    - Should we continue deliberation?
    - Is this genuine convergence or echo chamber?
    - Are we getting diminishing returns?
    """
    round_number: int

    # Geometry signals (embedding-space)
    centroid_distance: float = 0.0  # Distance from centroid to individual positions
    radius: float = 0.0  # Spread of positions around centroid
    velocity: float = 0.0  # Rate of change from previous round
    cluster_count: int = 1  # Number of distinct position clusters

    # Entropy signals (information-theoretic)
    content_entropy: float = 0.0  # Shannon entropy of content
    compression_ratio: float = 0.0  # Gzip compression ratio
    ngram_overlap: float = 0.0  # N-gram overlap between models

    # Novelty signals
    novelty_rate: float = 0.0  # Fraction of new claims vs. repeated
    minhash_similarity: float = 0.0  # MinHash set similarity
    residual_claims: int = 0  # New claims not in previous round

    # Disagreement signals
    explicit_disagreements: int = 0  # Counted from Crux Ledger
    minority_strength: float = 0.0  # Strength of minority opinions

    # Derived scores
    convergence_score: float = 0.0  # 0-1: Overall convergence estimate
    echo_chamber_risk: float = 0.0  # 0-1: Risk of false consensus
    continue_value: float = 0.0  # Expected value of continuing

    # Decision
    should_continue: bool = True
    stop_reason: Optional[str] = None


class ConvergenceEngine:
    """
    Multi-signal convergence detection for V4 deliberation.

    Unlike V3's simple similarity threshold, this engine:
    1. Tracks multiple independent signals
    2. Detects echo chambers via compression/entropy
    3. Preserves valuable disagreement
    4. Uses geometric analysis of positions
    """

    # Thresholds (tunable)
    THRESHOLDS = {
        "radius_converged": 0.1,  # Cluster is tight
        "velocity_stable": 0.02,  # Position is stable
        "entropy_saturated": 0.85,  # Information saturation
        "novelty_diminishing": 0.15,  # Little new content
        "compression_echo": 0.3,  # High compression = echo chamber
        "ngram_overlap_echo": 0.7,  # High n-gram overlap = echo
        "minority_preserve": 0.25,  # Preserve if minority strong
    }

    def __init__(self, history_depth: int = 5, model_names: List[str] = None):
        """
        Initialize convergence engine.

        Args:
            history_depth: Number of rounds to track for velocity/trends
            model_names: List of model names for tracking
        """
        self.history_depth = history_depth
        self.model_names = model_names or ['openai', 'gemini', 'grok']
        self.signal_history: List[ConvergenceSignals] = []
        self.claim_history: List[set] = []
        self.synthesis_history: List[Tuple[str, str]] = []  # (synthesis, round_id)

    def add_synthesis(self, synthesis: str, round_id: str):
        """
        Add a synthesis to the history for convergence tracking.

        Args:
            synthesis: The synthesis text from a round
            round_id: Identifier for this round
        """
        self.synthesis_history.append((synthesis, round_id))

        # Keep history bounded
        if len(self.synthesis_history) > self.history_depth:
            self.synthesis_history = self.synthesis_history[-self.history_depth:]

    def evaluate(self, min_rounds: int = 2, max_rounds: int = 5) -> ConvergenceDecision:
        """
        Evaluate current convergence state and return decision.

        This is the main entry point for the V4 orchestrator.

        Returns:
            ConvergenceDecision with should_stop, reason, and signals
        """
        # If we have signal history, use the latest
        if self.signal_history:
            latest = self.signal_history[-1]
            return ConvergenceDecision(
                should_stop=not latest.should_continue,
                reason=latest.stop_reason or "continue",
                signals=latest,
                confidence=latest.convergence_score
            )

        # If we have synthesis history but no signals, analyze now
        if self.synthesis_history:
            # Create pseudo-responses from syntheses
            recent = self.synthesis_history[-3:]
            responses = {f"synth_{i}": s for i, (s, _) in enumerate(recent)}

            signals = self.analyze(
                round_number=len(self.synthesis_history),
                model_responses=responses,
                min_rounds=min_rounds,
                max_rounds=max_rounds
            )

            return ConvergenceDecision(
                should_stop=not signals.should_continue,
                reason=signals.stop_reason or "continue",
                signals=signals,
                confidence=signals.convergence_score
            )

        # No data - default to continue
        return ConvergenceDecision(
            should_stop=False,
            reason="no_data",
            signals=ConvergenceSignals(round_number=0),
            confidence=0.0
        )

    def _compute_entropy(self, texts: List[str]) -> float:
        """
        Compute Shannon entropy of text content.

        High entropy = diverse content
        Low entropy = repetitive content
        """
        combined = " ".join(texts)
        char_counts = Counter(combined.lower())
        total = sum(char_counts.values())

        if total == 0:
            return 0.0

        entropy = 0.0
        for count in char_counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)

        # Normalize by max possible entropy
        max_entropy = math.log2(len(char_counts)) if char_counts else 1
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def _compute_compression_ratio(self, texts: List[str]) -> float:
        """
        Compute compression ratio as echo chamber detector.

        High compression = repetitive content (potential echo chamber)
        Low compression = diverse content
        """
        combined = " ".join(texts).encode('utf-8')
        if len(combined) == 0:
            return 0.0

        compressed = zlib.compress(combined)
        ratio = len(compressed) / len(combined)

        return 1.0 - ratio  # Invert so high = more repetitive

    def _compute_ngram_overlap(self, texts: List[str], n: int = 3) -> float:
        """
        Compute n-gram overlap between texts.

        High overlap = similar content structure
        """
        def get_ngrams(text: str) -> set:
            words = text.lower().split()
            return set(tuple(words[i:i+n]) for i in range(len(words)-n+1))

        if len(texts) < 2:
            return 0.0

        all_ngrams = [get_ngrams(t) for t in texts]

        # Pairwise Jaccard similarity
        total_sim = 0.0
        pairs = 0

        for i in range(len(all_ngrams)):
            for j in range(i+1, len(all_ngrams)):
                set_i, set_j = all_ngrams[i], all_ngrams[j]
                if set_i or set_j:
                    intersection = len(set_i & set_j)
                    union = len(set_i | set_j)
                    total_sim += intersection / union if union > 0 else 0
                    pairs += 1

        return total_sim / pairs if pairs > 0 else 0.0

    def _compute_minhash_similarity(self, texts: List[str], num_hashes: int = 100) -> float:
        """
        Compute MinHash similarity for novelty detection.

        MinHash is efficient for set similarity at scale.
        """
        def minhash_signature(text: str) -> List[int]:
            """Generate MinHash signature."""
            # Use word-level shingles
            words = text.lower().split()
            shingles = set(tuple(words[i:i+3]) for i in range(len(words)-2))

            if not shingles:
                return [0] * num_hashes

            signature = []
            for i in range(num_hashes):
                min_hash = float('inf')
                for shingle in shingles:
                    h = hashlib.md5(f"{i}:{shingle}".encode()).hexdigest()
                    hash_val = int(h[:8], 16)
                    min_hash = min(min_hash, hash_val)
                signature.append(min_hash if min_hash != float('inf') else 0)

            return signature

        if len(texts) < 2:
            return 0.0

        signatures = [minhash_signature(t) for t in texts]

        # Pairwise similarity
        total_sim = 0.0
        pairs = 0

        for i in range(len(signatures)):
            for j in range(i+1, len(signatures)):
                matches = sum(1 for a, b in zip(signatures[i], signatures[j]) if a == b)
                total_sim += matches / num_hashes
                pairs += 1

        return total_sim / pairs if pairs > 0 else 0.0

    def _extract_claims(self, text: str) -> set:
        """
        Extract claim-like statements from text.

        Used for novelty tracking - what new claims appeared?
        """
        claims = set()

        # Extract sentences that look like claims
        sentences = text.replace('!', '.').replace('?', '.').split('.')

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Too short
                continue
            if len(sentence) > 200:  # Too long, truncate
                sentence = sentence[:200]

            # Skip questions and meta-statements
            if '?' in sentence:
                continue
            if any(skip in sentence.lower() for skip in ['i think', 'perhaps', 'maybe']):
                continue

            # Normalize for comparison
            normalized = ' '.join(sentence.lower().split())
            claims.add(normalized)

        return claims

    def _compute_novelty(self, current_claims: set) -> Tuple[float, int]:
        """
        Compute novelty rate against historical claims.

        Returns (novelty_rate, residual_claims)
        """
        if not self.claim_history:
            return 1.0, len(current_claims)

        historical = set()
        for prev in self.claim_history[-3:]:  # Last 3 rounds
            historical.update(prev)

        if not current_claims:
            return 0.0, 0

        new_claims = current_claims - historical
        novelty_rate = len(new_claims) / len(current_claims)
        residual = len(new_claims)

        return novelty_rate, residual

    def _compute_geometry(
        self,
        responses: Dict[str, str],
        previous_signals: Optional[ConvergenceSignals]
    ) -> Tuple[float, float, float, int]:
        """
        Compute geometric signals (radius, velocity, clusters).

        In the absence of real embeddings, we use text-based proxies.
        """
        # Use n-gram vectors as proxy for position
        def text_to_vector(text: str) -> Counter:
            words = text.lower().split()
            return Counter(words)

        vectors = [text_to_vector(r) for r in responses.values()]

        if len(vectors) < 2:
            return 0.0, 0.0, 0.0, 1

        # Compute centroid
        centroid = Counter()
        for v in vectors:
            centroid.update(v)
        for key in centroid:
            centroid[key] /= len(vectors)

        # Compute radius (average distance from centroid)
        def cosine_distance(v1: Counter, v2: Counter) -> float:
            keys = set(v1.keys()) | set(v2.keys())
            if not keys:
                return 1.0
            dot = sum(v1.get(k, 0) * v2.get(k, 0) for k in keys)
            norm1 = math.sqrt(sum(v1.get(k, 0)**2 for k in keys))
            norm2 = math.sqrt(sum(v2.get(k, 0)**2 for k in keys))
            if norm1 == 0 or norm2 == 0:
                return 1.0
            return 1.0 - (dot / (norm1 * norm2))

        distances = [cosine_distance(v, centroid) for v in vectors]
        radius = sum(distances) / len(distances)

        # Compute velocity (change from previous)
        velocity = 0.0
        if previous_signals:
            velocity = abs(radius - previous_signals.radius)

        # Cluster count (simple: if radius low, 1 cluster)
        cluster_count = 1 if radius < 0.3 else min(len(vectors), int(radius * 5) + 1)

        centroid_distance = radius  # Same as radius in this proxy

        return centroid_distance, radius, velocity, cluster_count

    def analyze(
        self,
        round_number: int,
        model_responses: Dict[str, str],
        crux_ledger: Optional[Any] = None,
        min_rounds: int = 2,
        max_rounds: int = 5
    ) -> ConvergenceSignals:
        """
        Analyze convergence signals for the current round.

        Args:
            round_number: Current round number
            model_responses: Dict of model_name -> response
            crux_ledger: Optional CruxLedger for disagreement tracking
            min_rounds: Minimum rounds before allowing stop
            max_rounds: Maximum rounds (hard limit)

        Returns:
            ConvergenceSignals with all metrics and decision
        """
        texts = list(model_responses.values())
        previous = self.signal_history[-1] if self.signal_history else None

        # Compute all signals
        signals = ConvergenceSignals(round_number=round_number)

        # Geometry signals
        (signals.centroid_distance, signals.radius,
         signals.velocity, signals.cluster_count) = self._compute_geometry(
            model_responses, previous
        )

        # Entropy signals
        signals.content_entropy = self._compute_entropy(texts)
        signals.compression_ratio = self._compute_compression_ratio(texts)
        signals.ngram_overlap = self._compute_ngram_overlap(texts)

        # Novelty signals
        current_claims = set()
        for text in texts:
            current_claims.update(self._extract_claims(text))

        signals.novelty_rate, signals.residual_claims = self._compute_novelty(
            current_claims
        )
        signals.minhash_similarity = self._compute_minhash_similarity(texts)

        # Disagreement signals (from Crux Ledger if available)
        if crux_ledger:
            signals.explicit_disagreements = len(getattr(
                crux_ledger, 'disagreement_cruxes', []
            ))
            # Calculate minority strength from cruxes
            cruxes = getattr(crux_ledger, 'cruxes', [])
            if cruxes:
                signals.minority_strength = sum(
                    c.minority_score for c in cruxes
                ) / len(cruxes)

        # Derived scores
        signals.convergence_score = self._compute_convergence_score(signals)
        signals.echo_chamber_risk = self._compute_echo_risk(signals)
        signals.continue_value = self._compute_continue_value(signals)

        # Decision
        signals.should_continue, signals.stop_reason = self._make_decision(
            signals, min_rounds, max_rounds
        )

        # Update history
        self.signal_history.append(signals)
        self.claim_history.append(current_claims)

        # Trim history
        if len(self.signal_history) > self.history_depth:
            self.signal_history = self.signal_history[-self.history_depth:]
            self.claim_history = self.claim_history[-self.history_depth:]

        return signals

    def _compute_convergence_score(self, signals: ConvergenceSignals) -> float:
        """
        Compute overall convergence score (0-1).

        High score = positions are converging
        """
        # Weighted combination of signals
        score = 0.0

        # Tight cluster = converging
        if signals.radius < self.THRESHOLDS["radius_converged"]:
            score += 0.3

        # Low velocity = stable
        if signals.velocity < self.THRESHOLDS["velocity_stable"]:
            score += 0.2

        # High n-gram overlap = similar positions
        score += signals.ngram_overlap * 0.3

        # Low novelty = not much new
        score += (1.0 - signals.novelty_rate) * 0.2

        return min(score, 1.0)

    def _compute_echo_risk(self, signals: ConvergenceSignals) -> float:
        """
        Compute echo chamber risk (0-1).

        High risk = potential false consensus
        """
        risk = 0.0

        # High compression = repetitive content
        if signals.compression_ratio > self.THRESHOLDS["compression_echo"]:
            risk += 0.4

        # Very high n-gram overlap
        if signals.ngram_overlap > self.THRESHOLDS["ngram_overlap_echo"]:
            risk += 0.3

        # Very low disagreement with high convergence
        if signals.explicit_disagreements == 0 and signals.convergence_score > 0.8:
            risk += 0.3

        return min(risk, 1.0)

    def _compute_continue_value(self, signals: ConvergenceSignals) -> float:
        """
        Compute expected value of continuing deliberation.

        High value = worth continuing
        """
        value = 0.0

        # High novelty = new insights possible
        value += signals.novelty_rate * 0.4

        # Strong minority = valuable disagreement
        if signals.minority_strength > self.THRESHOLDS["minority_preserve"]:
            value += 0.3

        # Many residual claims = unresolved content
        value += min(signals.residual_claims / 20, 0.3)

        return min(value, 1.0)

    def _make_decision(
        self,
        signals: ConvergenceSignals,
        min_rounds: int,
        max_rounds: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Make continue/stop decision based on signals.

        Returns (should_continue, reason)
        """
        round_num = signals.round_number

        # Hard limits
        if round_num < min_rounds:
            return True, None

        if round_num >= max_rounds:
            return False, "max_rounds_reached"

        # Echo chamber detection - continue to break it
        if signals.echo_chamber_risk > 0.6:
            return True, "echo_chamber_detected"

        # Strong minority - preserve disagreement
        if signals.minority_strength > self.THRESHOLDS["minority_preserve"]:
            return True, "preserving_minority"

        # High convergence + low echo risk = genuine consensus
        if signals.convergence_score > 0.8 and signals.echo_chamber_risk < 0.3:
            return False, "genuine_consensus"

        # Saturation detected
        if (signals.novelty_rate < self.THRESHOLDS["novelty_diminishing"] and
            signals.velocity < self.THRESHOLDS["velocity_stable"]):
            return False, "saturation_detected"

        # Continue value assessment
        if signals.continue_value < 0.2:
            return False, "low_continue_value"

        return True, None

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of convergence analysis."""
        if not self.signal_history:
            return {"status": "no_analysis"}

        latest = self.signal_history[-1]

        return {
            "round": latest.round_number,
            "convergence_score": round(latest.convergence_score, 3),
            "echo_chamber_risk": round(latest.echo_chamber_risk, 3),
            "continue_value": round(latest.continue_value, 3),
            "should_continue": latest.should_continue,
            "stop_reason": latest.stop_reason,
            "signals": {
                "radius": round(latest.radius, 3),
                "velocity": round(latest.velocity, 3),
                "entropy": round(latest.content_entropy, 3),
                "novelty": round(latest.novelty_rate, 3),
                "minority_strength": round(latest.minority_strength, 3)
            },
            "history_length": len(self.signal_history)
        }


if __name__ == "__main__":
    # Test the convergence engine
    engine = ConvergenceEngine()

    # Simulate 3 rounds with model responses
    rounds = [
        {
            "openai": "We should adopt a microservices architecture for better scalability. This allows independent deployment and team autonomy. The main risk is complexity in orchestration.",
            "gemini": "Microservices offer flexibility but introduce significant operational overhead. Consider starting with modular monolith. The team size matters here.",
            "grok": "Why not both? Start monolithic, extract services as needed. Don't over-engineer for scale you don't have yet. Most startups fail from building wrong thing, not scaling."
        },
        {
            "openai": "I agree with the pragmatic approach - start simple. Modular monolith with clear boundaries enables future extraction. This aligns team velocity with actual needs.",
            "gemini": "Yes, modular monolith is the consensus. Key is defining clear module boundaries now. Use dependency injection to enable future extraction.",
            "grok": "Convergence emerging. The answer is: domain-driven boundaries in monolith, services when team/scale demands. Simple."
        },
        {
            "openai": "Strong consensus on modular monolith with domain-driven design. Extract to services when: team grows >8, module has different scaling needs, or deployment independence required.",
            "gemini": "Agreed. Clear criteria for extraction: team size, scaling divergence, deployment independence. The architecture decision is settled.",
            "grok": "Consensus achieved. Next question should be: how do we define the module boundaries?"
        }
    ]

    for i, responses in enumerate(rounds):
        signals = engine.analyze(
            round_number=i + 1,
            model_responses=responses,
            min_rounds=2,
            max_rounds=5
        )
        print(f"\n=== Round {i+1} ===")
        print(f"Convergence: {signals.convergence_score:.2f}")
        print(f"Echo Risk: {signals.echo_chamber_risk:.2f}")
        print(f"Continue Value: {signals.continue_value:.2f}")
        print(f"Should Continue: {signals.should_continue}")
        print(f"Stop Reason: {signals.stop_reason}")

    print(f"\n=== Final Summary ===")
    print(engine.get_summary())

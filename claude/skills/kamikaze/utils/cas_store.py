#!/usr/bin/env python3
"""
Kamikaze V4: Content-Addressable Storage (CAS) Backbone

CAS provides immutable, content-addressed storage for all deliberation artifacts.
This is the M0 (foundational) layer that enables:
- Deduplication across runs
- Auditability and provenance tracking
- Stable referencing for handoffs
- "Open writes, typed reads" pattern

Design Principles (from V4 deliberation):
1. Log everything (including garbage) to capture Black Swans
2. Two-tier writes: Raw CAS (open) → Scored Crux promotion
3. Content-addressing via SHA-256 for determinism
4. Provenance envelopes track artifact lineage
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


@dataclass
class CASArtifact:
    """
    An immutable artifact stored in CAS.

    Every artifact has:
    - content_hash: SHA-256 of the content (the address)
    - content_type: Type tag for typed reads
    - content: The actual data (raw or structured)
    - provenance: Chain of where this artifact came from
    - metadata: Flexible metadata for filtering
    """
    content_hash: str
    content_type: str  # 'transcript', 'synthesis', 'crux', 'embedding', 'signal'
    content: Any
    provenance: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ProvenanceEnvelope:
    """
    Tracks artifact lineage for auditability.

    Allows answering: "Where did this insight come from?"
    """
    source_hashes: List[str]  # Parent artifact hashes
    transformation: str  # What operation produced this
    model: Optional[str] = None  # Which model (if AI-generated)
    round_id: Optional[str] = None
    confidence: float = 0.0


class CASStore:
    """
    Content-Addressable Storage for Kamikaze V4.

    Implements the "thermodynamic" storage model:
    - Open writes: Accept all artifacts without filtering
    - Typed reads: Query by type, provenance, time, etc.
    - Immutable: Once written, artifacts never change
    - Deduplication: Same content = same hash = stored once
    """

    def __init__(self, base_dir: str = None):
        """
        Initialize CAS store.

        Args:
            base_dir: Base directory for storage. Defaults to ~/.kamikaze/cas
        """
        if base_dir is None:
            base_dir = os.path.expanduser("~/.kamikaze/cas")

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Subdirectories for organization (but all addressed by hash)
        (self.base_dir / "artifacts").mkdir(exist_ok=True)
        (self.base_dir / "index").mkdir(exist_ok=True)

        # In-memory index for fast lookups (loaded from disk)
        self._index: Dict[str, CASArtifact] = {}
        self._type_index: Dict[str, List[str]] = {}  # type -> [hashes]
        self._load_index()

    def _compute_hash(self, content: Any) -> str:
        """Compute SHA-256 hash of content."""
        if isinstance(content, str):
            data = content.encode('utf-8')
        elif isinstance(content, (dict, list)):
            data = json.dumps(content, sort_keys=True).encode('utf-8')
        else:
            data = str(content).encode('utf-8')

        return hashlib.sha256(data).hexdigest()

    def _artifact_path(self, content_hash: str) -> Path:
        """Get file path for artifact by hash (sharded by first 2 chars)."""
        shard = content_hash[:2]
        return self.base_dir / "artifacts" / shard / f"{content_hash}.json"

    def _load_index(self):
        """Load index from disk."""
        index_file = self.base_dir / "index" / "main_index.json"
        type_index_file = self.base_dir / "index" / "type_index.json"

        if index_file.exists():
            try:
                with open(index_file) as f:
                    for line in f:
                        data = json.loads(line)
                        artifact = CASArtifact(**data)
                        self._index[artifact.content_hash] = artifact
            except Exception:
                pass  # Start fresh if index is corrupted

        if type_index_file.exists():
            try:
                with open(type_index_file) as f:
                    self._type_index = json.load(f)
            except Exception:
                self._type_index = {}

    def _save_artifact(self, artifact: CASArtifact):
        """Save artifact to disk."""
        path = self._artifact_path(artifact.content_hash)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(asdict(artifact), f, indent=2)

    def _update_index(self, artifact: CASArtifact):
        """Update in-memory and on-disk indices."""
        self._index[artifact.content_hash] = artifact

        # Update type index
        if artifact.content_type not in self._type_index:
            self._type_index[artifact.content_type] = []
        if artifact.content_hash not in self._type_index[artifact.content_type]:
            self._type_index[artifact.content_type].append(artifact.content_hash)

        # Append to index file (JSONL for efficiency)
        index_file = self.base_dir / "index" / "main_index.json"
        with open(index_file, 'a') as f:
            f.write(json.dumps(asdict(artifact)) + '\n')

        # Save type index
        type_index_file = self.base_dir / "index" / "type_index.json"
        with open(type_index_file, 'w') as f:
            json.dump(self._type_index, f)

    # =========================================================================
    # PUBLIC API: Write Operations
    # =========================================================================

    def put(self, content: Any, content_type: str,
            provenance: Optional[Dict] = None,
            metadata: Optional[Dict] = None) -> str:
        """
        Store an artifact in CAS.

        This is an "open write" - accepts all content without filtering.
        Deduplicates: if content already exists, returns existing hash.

        Args:
            content: The content to store (str, dict, list, etc.)
            content_type: Type tag ('transcript', 'synthesis', 'crux', etc.)
            provenance: Optional provenance envelope
            metadata: Optional metadata for filtering

        Returns:
            content_hash: The SHA-256 hash (address) of the artifact
        """
        content_hash = self._compute_hash(content)

        # Deduplication: check if already exists
        if content_hash in self._index:
            return content_hash

        # Create artifact
        artifact = CASArtifact(
            content_hash=content_hash,
            content_type=content_type,
            content=content,
            provenance=provenance or {},
            metadata=metadata or {}
        )

        # Persist
        self._save_artifact(artifact)
        self._update_index(artifact)

        return content_hash

    def put_with_provenance(self, content: Any, content_type: str,
                            source_hashes: List[str],
                            transformation: str,
                            model: Optional[str] = None,
                            confidence: float = 0.0,
                            metadata: Optional[Dict] = None) -> str:
        """
        Store an artifact with explicit provenance tracking.

        Args:
            content: The content to store
            content_type: Type tag
            source_hashes: List of parent artifact hashes
            transformation: Description of operation that produced this
            model: Model that generated this (if AI)
            confidence: Confidence score for this artifact
            metadata: Optional additional metadata

        Returns:
            content_hash: The SHA-256 hash of the artifact
        """
        provenance = {
            "source_hashes": source_hashes,
            "transformation": transformation,
            "model": model,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }

        return self.put(content, content_type, provenance, metadata)

    # =========================================================================
    # PUBLIC API: Read Operations (Typed Reads)
    # =========================================================================

    def get(self, content_hash: str) -> Optional[CASArtifact]:
        """
        Retrieve an artifact by its hash.

        Args:
            content_hash: The SHA-256 hash of the artifact

        Returns:
            CASArtifact if found, None otherwise
        """
        # Check in-memory index first
        if content_hash in self._index:
            return self._index[content_hash]

        # Try loading from disk
        path = self._artifact_path(content_hash)
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                artifact = CASArtifact(**data)
                self._index[content_hash] = artifact
                return artifact

        return None

    def get_content(self, content_hash: str) -> Optional[Any]:
        """Get just the content of an artifact."""
        artifact = self.get(content_hash)
        return artifact.content if artifact else None

    def get_by_type(self, content_type: str,
                    limit: int = 100,
                    after: Optional[str] = None) -> List[CASArtifact]:
        """
        Query artifacts by type (typed read).

        Args:
            content_type: Type to filter by
            limit: Max number of results
            after: Timestamp to filter after (ISO format)

        Returns:
            List of matching artifacts, newest first
        """
        hashes = self._type_index.get(content_type, [])
        results = []

        for h in reversed(hashes[-limit:]):
            artifact = self.get(h)
            if artifact:
                if after is None or artifact.timestamp > after:
                    results.append(artifact)
                    if len(results) >= limit:
                        break

        return results

    def get_by_metadata(self, key: str, value: Any,
                        content_type: Optional[str] = None,
                        limit: int = 100) -> List[CASArtifact]:
        """
        Query artifacts by metadata key-value.

        Args:
            key: Metadata key to match
            value: Value to match
            content_type: Optional type filter
            limit: Max results

        Returns:
            List of matching artifacts
        """
        results = []

        for artifact in self._index.values():
            if content_type and artifact.content_type != content_type:
                continue
            if artifact.metadata.get(key) == value:
                results.append(artifact)
                if len(results) >= limit:
                    break

        return results

    def get_provenance_chain(self, content_hash: str,
                             max_depth: int = 10) -> List[CASArtifact]:
        """
        Trace the provenance chain of an artifact.

        Returns the artifact and all its ancestors up to max_depth.
        """
        chain = []
        visited = set()
        to_visit = [content_hash]

        while to_visit and len(chain) < max_depth:
            current_hash = to_visit.pop(0)

            if current_hash in visited:
                continue
            visited.add(current_hash)

            artifact = self.get(current_hash)
            if artifact:
                chain.append(artifact)

                # Add parents to visit
                source_hashes = artifact.provenance.get("source_hashes", [])
                to_visit.extend(source_hashes)

        return chain

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def exists(self, content_hash: str) -> bool:
        """Check if an artifact exists."""
        return content_hash in self._index or self._artifact_path(content_hash).exists()

    def count(self, content_type: Optional[str] = None) -> int:
        """Count artifacts, optionally filtered by type."""
        if content_type:
            return len(self._type_index.get(content_type, []))
        return len(self._index)

    def stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        type_counts = {t: len(h) for t, h in self._type_index.items()}

        return {
            "total_artifacts": len(self._index),
            "by_type": type_counts,
            "storage_path": str(self.base_dir),
            "index_loaded": len(self._index)
        }


# =============================================================================
# Module-level convenience functions
# =============================================================================

_default_store: Optional[CASStore] = None

def get_default_store() -> CASStore:
    """Get or create the default CAS store."""
    global _default_store
    if _default_store is None:
        _default_store = CASStore()
    return _default_store

def cas_put(content: Any, content_type: str, **kwargs) -> str:
    """Convenience function to store in default CAS."""
    return get_default_store().put(content, content_type, **kwargs)

def cas_get(content_hash: str) -> Optional[CASArtifact]:
    """Convenience function to retrieve from default CAS."""
    return get_default_store().get(content_hash)


if __name__ == "__main__":
    # Quick test
    store = CASStore()

    # Store a test artifact
    hash1 = store.put(
        content={"test": "data", "value": 123},
        content_type="test",
        metadata={"run_id": "test-001"}
    )
    print(f"Stored: {hash1}")

    # Retrieve it
    artifact = store.get(hash1)
    print(f"Retrieved: {artifact}")

    # Store with provenance
    hash2 = store.put_with_provenance(
        content="Derived insight",
        content_type="synthesis",
        source_hashes=[hash1],
        transformation="test_transform",
        model="gpt-4"
    )
    print(f"Derived: {hash2}")

    # Trace provenance
    chain = store.get_provenance_chain(hash2)
    print(f"Provenance chain: {len(chain)} artifacts")

    # Stats
    print(f"Stats: {store.stats()}")

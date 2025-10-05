#!/usr/bin/env python3
"""
DocChunk model for vector embeddings and search.
"""

from typing import Dict, List, Optional
import json


class DocChunk:
    """Represents a document chunk with vector embeddings for semantic search."""

    def __init__(
        self,
        text: str,
        vector: List[float],
        metadata: Optional[Dict] = None,
        chunk_id: Optional[str] = None,
        repo: Optional[str] = None,
        file_path: Optional[str] = None
    ):
        """Initialize DocChunk."""
        self.text = text
        self.vector = vector
        self.metadata = metadata or {}
        self.chunk_id = chunk_id or f"chunk_{hash(text) % 1000000}"
        self.repo = repo
        self.file_path = file_path

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "vector": self.vector,
            "metadata": self.metadata,
            "chunk_id": self.chunk_id,
            "repo": self.repo,
            "file_path": self.file_path
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DocChunk':
        """Create from dictionary."""
        return cls(
            text=data["text"],
            vector=data["vector"],
            metadata=data.get("metadata", {}),
            chunk_id=data.get("chunk_id"),
            repo=data.get("repo"),
            file_path=data.get("file_path")
        )

    def to_weaviate_format(self) -> Dict:
        """Convert to Weaviate data object format."""
        return {
            "chunkText": self.text,
            "vector": self.vector,
            "metadata": json.dumps(self.metadata) if self.metadata else None,
            "repo": self.repo,
            "file": self.file_path,
            "chunkId": self.chunk_id
        }

    def calculate_similarity(self, other_vector: List[float]) -> float:
        """Calculate cosine similarity with another vector."""
        import math

        # Cosine similarity calculation
        dot_product = sum(a * b for a, b in zip(self.vector, other_vector))
        norm_self = math.sqrt(sum(a * a for a in self.vector))
        norm_other = math.sqrt(sum(b * b for b in other_vector))

        if norm_self == 0 or norm_other == 0:
            return 0.0

        return dot_product / (norm_self * norm_other)

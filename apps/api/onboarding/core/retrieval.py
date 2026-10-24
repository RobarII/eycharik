"""One retrieval policy, read by every backend.

Retrieval is the stage where two implementations drift silently: the in-memory backend exists to
test ranking without a database, and the moment it chunks, embeds or gates differently from the
Postgres path, the tests stop being evidence about production. The pieces that used to be restated
in both places — the chunk window, the embedding view, the lexical gate, the fusion weights, the
candidate budget — live here as one value.

What stays backend-specific is honest: Postgres orders the lexical list with ``ts_rank_cd``, the
in-memory backend orders it by token overlap. A different ranking function over the same admitted
set is a different opinion about order; a different *admitted set* is a different product.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .chunking import DEFAULT_MAX_CHARS, DEFAULT_OVERLAP_CHARS
from .models import Chunk, ChunkId
from .ranking import LEXICAL_WEIGHT, reciprocal_rank_fusion

# Three covered question words is evidence that a lexical hit is about the question rather than
# about one shared stopword; a two-word question must cover both. Measured on the golden set against
# the shipped corpus; see docs/measurements/2026-10-24-eval-retrieval-lexical-gated-05.md.
DEFAULT_COVERAGE_FLOOR = 3
# Candidates per retriever before fusion. Recall is cheap, the prompt is not.
DEFAULT_OVERFETCH = 40


@dataclass(frozen=True, slots=True)
class RetrievalPolicy:
    max_chars: int = DEFAULT_MAX_CHARS
    overlap_chars: int = DEFAULT_OVERLAP_CHARS
    lexical_weight: float = LEXICAL_WEIGHT
    coverage_floor: int = DEFAULT_COVERAGE_FLOOR
    overfetch: int = DEFAULT_OVERFETCH

    def __post_init__(self) -> None:
        if self.max_chars <= 0:
            raise ValueError("max_chars must be positive")
        if not 0 <= self.overlap_chars < self.max_chars:
            raise ValueError("overlap_chars must be in [0, max_chars)")
        if not 0.0 < self.lexical_weight <= 1.0:
            raise ValueError("lexical_weight must be in (0, 1]")
        if self.coverage_floor < 1:
            raise ValueError("coverage_floor must be at least 1")
        if self.overfetch < 1:
            raise ValueError("overfetch must be at least 1")

    def embedding_view(self, chunk: Chunk) -> str:
        """What the embedder sees: the contextual prefix plus the quotable text (ADR 0016)."""
        return chunk.embedding_text

    def lexical_view(self, chunk: Chunk) -> str:
        """What the lexical index sees. The same view as the embedder, or the two disagree."""
        return chunk.embedding_text

    def coverage_required(self, terms: int) -> int:
        """How many distinct question terms a lexical hit must contain to enter the fusion."""
        return min(self.coverage_floor, max(terms, 1))

    def lexical_admits(self, covered: int, terms: int) -> bool:
        return covered >= self.coverage_required(terms)

    def fuse(
        self,
        semantic: Sequence[ChunkId],
        lexical: Sequence[ChunkId],
        *,
        limit: int | None = None,
    ) -> tuple[tuple[ChunkId, float], ...]:
        """The one fusion: vector order at the head, the lexical list allowed to promote a find."""
        return reciprocal_rank_fusion(
            [semantic, lexical],
            weights=(1.0, self.lexical_weight),
            limit=limit,
        )

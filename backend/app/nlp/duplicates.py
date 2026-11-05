"""Duplicate detection with sentence embeddings and cosine similarity.

  1. A sentence-transformers model turns each requirement into a list of numbers
     (an "embedding") that captures its meaning.
  2. Cosine similarity compares two embeddings. 1.0 means the same meaning, 0 means unrelated.
  3. Pairs above the threshold are shown to a person. Nothing is merged or deleted,
     because high similarity does not prove that two requirements are duplicates.
"""
from functools import lru_cache

from ..config import EMBEDDING_MODEL
from .preprocess import has_negation, numbers_in


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer
    # CPU is fast enough for this small model, and leaves the GPU free for Ollama.
    return SentenceTransformer(EMBEDDING_MODEL, device="cpu")


def similarity_matrix(texts: list[str]):
    """Returns a table where cell [i][j] is the similarity of texts i and j."""
    embeddings = get_embedding_model().encode(texts, normalize_embeddings=True)
    return embeddings @ embeddings.T  # for normalised vectors, this is cosine similarity


def similar_pairs(texts: list[str], threshold: float) -> list[tuple[int, int, float]]:
    """All pairs (i, j, score) with a score at or above the threshold, highest first."""
    if len(texts) < 2:
        return []
    scores = similarity_matrix(texts)
    pairs = [
        (i, j, round(float(scores[i][j]), 3))
        for i in range(len(texts))
        for j in range(i + 1, len(texts))
        if scores[i][j] >= threshold
    ]
    return sorted(pairs, key=lambda pair: -pair[2])


def review_reason(a: str, b: str, score: float) -> str:
    """Plain-language reason for showing this pair, including warnings about differences."""
    if a.strip().lower() == b.strip().lower():
        reason = "The wording is identical."
    elif score >= 0.9:
        reason = "The wording or meaning is very close."
    else:
        reason = "The meaning looks similar, but check for differences."
    if has_negation(a) != has_negation(b):
        reason += " Only one is negated, so this may be a contradiction, not a duplicate."
    if numbers_in(a) != numbers_in(b):
        reason += " The numbers differ, so these may be conflicting limits."
    return reason

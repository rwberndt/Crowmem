def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


COLD_START_NOVELTY = 0.5


def compute_novelty(embedding: list[float], recent_embeddings: list[list[float]]) -> float:
    """1 - max cosine similarity to recent memories (guide section 8).

    Cold start (no prior episodes to compare against) returns a neutral
    0.5 rather than a maximal 1.0: treating "nothing to compare against"
    as "maximally novel" would let novelty alone push even a trivial first
    event (e.g. "opened README") over the encode threshold on a brand-new
    project -- exactly the single-signal domination design principle 5
    warns against.
    """
    if not recent_embeddings:
        return COLD_START_NOVELTY
    max_sim = max(cosine_similarity(embedding, other) for other in recent_embeddings)
    return max(0.0, 1.0 - max_sim)

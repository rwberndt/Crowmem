"""Canned, deterministic stand-ins for the Anthropic calls, used so tests
never hit the live API (guide section 30: "do not rely on live LLM
responses in most unit tests... mock extraction outputs").
"""

from app.schemas.extraction import (
    BeliefCandidate,
    BeliefExtractionResult,
    BeliefRelationClassification,
    MemoryCandidate,
    MemoryExtractionResult,
)


def empty_memory_result(content: str, metadata: dict) -> MemoryExtractionResult:
    return MemoryExtractionResult(memories=[])


def empty_belief_result(content: str, metadata: dict) -> BeliefExtractionResult:
    return BeliefExtractionResult(beliefs=[])


def make_memory_extractor(candidate: MemoryCandidate):
    def _extract(content: str, metadata: dict) -> MemoryExtractionResult:
        return MemoryExtractionResult(memories=[candidate])

    return _extract


def make_belief_extractor(candidate: BeliefCandidate):
    def _extract(content: str, metadata: dict) -> BeliefExtractionResult:
        return BeliefExtractionResult(beliefs=[candidate])

    return _extract


def make_relation_classifier(relation: str, confidence: float = 0.9, rationale: str = "test"):
    def _classify(*args, **kwargs) -> BeliefRelationClassification:
        return BeliefRelationClassification(relation=relation, confidence=confidence, rationale=rationale)

    return _classify

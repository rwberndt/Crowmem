"""Canned, deterministic stand-ins for the Anthropic calls, used so tests
never hit the live API (guide section 30: "do not rely on live LLM
responses in most unit tests... mock extraction outputs").

Every real anthropic_client function returns (result, LlmUsage); these
fakes match that shape so a monkeypatched test exercises the same call
contract the real client does.
"""

from app.schemas.extraction import (
    BeliefCandidate,
    BeliefExtractionResult,
    BeliefRelationClassification,
    LlmUsage,
    MemoryCandidate,
    MemoryExtractionResult,
)

FAKE_USAGE = LlmUsage(model="fake-model", input_tokens=10, output_tokens=5)


def empty_memory_result(content: str, metadata: dict) -> tuple[MemoryExtractionResult, LlmUsage]:
    return MemoryExtractionResult(memories=[]), FAKE_USAGE


def empty_belief_result(content: str, metadata: dict) -> tuple[BeliefExtractionResult, LlmUsage]:
    return BeliefExtractionResult(beliefs=[]), FAKE_USAGE


def make_memory_extractor(candidate: MemoryCandidate):
    def _extract(content: str, metadata: dict) -> tuple[MemoryExtractionResult, LlmUsage]:
        return MemoryExtractionResult(memories=[candidate]), FAKE_USAGE

    return _extract


def make_belief_extractor(candidate: BeliefCandidate):
    def _extract(content: str, metadata: dict) -> tuple[BeliefExtractionResult, LlmUsage]:
        return BeliefExtractionResult(beliefs=[candidate]), FAKE_USAGE

    return _extract


def make_relation_classifier(relation: str, confidence: float = 0.9, rationale: str = "test"):
    def _classify(*args, **kwargs) -> tuple[BeliefRelationClassification, LlmUsage]:
        return BeliefRelationClassification(relation=relation, confidence=confidence, rationale=rationale), FAKE_USAGE

    return _classify

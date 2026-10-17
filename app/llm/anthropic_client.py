"""Boundary to the Anthropic API for memory-candidate extraction and belief
relation classification.

Invariant (guide section 35, #6): the LLM never directly mutates memory
state. Nothing in this module may import app.db, app.repositories, or any
SQLAlchemy session — it only returns validated Pydantic objects that calling
services decide how to apply. An API error or a malformed structured
response degrades to an empty/neutral result rather than raising, so the
pipeline never crashes on a bad LLM response -- but only those two failure
modes are caught; a real bug in this module is not disguised as "the LLM
chose not to extract anything."

Every function returns (result, LlmUsage): real token counts, captured
whenever the API call itself succeeded, even if validation afterward
failed -- tokens were spent either way.
"""

import json
from functools import lru_cache
from pathlib import Path

import anthropic
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.extraction import (
    BeliefExtractionResult,
    BeliefRelationClassification,
    LlmUsage,
    MemoryExtractionResult,
)

_PROMPTS_DIR = Path(__file__).parent / "prompts"

_EXTRACT_MEMORIES_TOOL = {
    "name": "extract_memories",
    "description": "Report zero or more durable memory candidates extracted from an event.",
    "input_schema": {
        "type": "object",
        "properties": {
            "memories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "memory_type": {
                            "type": "string",
                            "enum": [
                                "procedural", "failure", "constraint", "decision", "preference",
                                "environment", "fact", "workflow", "warning", "pattern",
                            ],
                        },
                        "risk_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "associations": {"type": "object", "additionalProperties": {"type": "string"}},
                    },
                    "required": ["content", "memory_type", "risk_score", "confidence", "associations"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["memories"],
        "additionalProperties": False,
    },
}

_EXTRACT_BELIEFS_TOOL = {
    "name": "extract_beliefs",
    "description": "Report zero or more durable subject-predicate-object belief candidates extracted from an event.",
    "input_schema": {
        "type": "object",
        "properties": {
            "beliefs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "predicate": {"type": "string"},
                        "object": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    },
                    "required": ["subject", "predicate", "object", "confidence"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["beliefs"],
        "additionalProperties": False,
    },
}

_CLASSIFY_RELATION_TOOL = {
    "name": "classify_belief_relation",
    "description": "Classify how a new belief candidate relates to an existing active belief.",
    "input_schema": {
        "type": "object",
        "properties": {
            "relation": {"type": "string", "enum": ["SUPPORTS", "SUPERSEDES", "CONTRADICTS", "REFINES"]},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "rationale": {"type": "string"},
        },
        "required": ["relation", "confidence", "rationale"],
        "additionalProperties": False,
    },
}


@lru_cache
def get_anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key)


@lru_cache
def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def _extract_tool_input(message: anthropic.types.Message, tool_name: str) -> dict | None:
    for block in message.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input
    return None


def extract_memories(episode_content: str, metadata: dict) -> tuple[MemoryExtractionResult, LlmUsage]:
    client = get_anthropic_client()
    settings = get_settings()
    system_prompt = _load_prompt("memory_extraction.md")
    user_message = f"Event content:\n{episode_content}\n\nMetadata:\n{json.dumps(metadata)}"
    zero_usage = LlmUsage(model=settings.anthropic_extraction_model)

    try:
        message = client.messages.create(
            model=settings.anthropic_extraction_model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            tools=[_EXTRACT_MEMORIES_TOOL],
            tool_choice={"type": "tool", "name": "extract_memories"},
        )
    except anthropic.APIError:
        return MemoryExtractionResult(memories=[]), zero_usage

    usage = LlmUsage(
        model=settings.anthropic_extraction_model,
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
    )
    tool_input = _extract_tool_input(message, "extract_memories")
    if tool_input is None:
        return MemoryExtractionResult(memories=[]), usage
    try:
        return MemoryExtractionResult.model_validate(tool_input), usage
    except ValidationError:
        return MemoryExtractionResult(memories=[]), usage


def extract_belief_candidates(episode_content: str, metadata: dict) -> tuple[BeliefExtractionResult, LlmUsage]:
    client = get_anthropic_client()
    settings = get_settings()
    system_prompt = _load_prompt("belief_candidate_extraction.md")
    user_message = f"Event content:\n{episode_content}\n\nMetadata:\n{json.dumps(metadata)}"
    zero_usage = LlmUsage(model=settings.anthropic_extraction_model)

    try:
        message = client.messages.create(
            model=settings.anthropic_extraction_model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            tools=[_EXTRACT_BELIEFS_TOOL],
            tool_choice={"type": "tool", "name": "extract_beliefs"},
        )
    except anthropic.APIError:
        return BeliefExtractionResult(beliefs=[]), zero_usage

    usage = LlmUsage(
        model=settings.anthropic_extraction_model,
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
    )
    tool_input = _extract_tool_input(message, "extract_beliefs")
    if tool_input is None:
        return BeliefExtractionResult(beliefs=[]), usage
    try:
        return BeliefExtractionResult.model_validate(tool_input), usage
    except ValidationError:
        return BeliefExtractionResult(beliefs=[]), usage


def classify_belief_relation(
    old_subject: str, old_predicate: str, old_object: str, new_object: str
) -> tuple[BeliefRelationClassification, LlmUsage]:
    client = get_anthropic_client()
    settings = get_settings()
    system_prompt = _load_prompt("belief_extraction.md")
    user_message = (
        f"Existing belief: {old_subject} {old_predicate} {old_object}\n"
        f"New candidate: {old_subject} {old_predicate} {new_object}"
    )
    zero_usage = LlmUsage(model=settings.anthropic_extraction_model)

    try:
        message = client.messages.create(
            model=settings.anthropic_extraction_model,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            tools=[_CLASSIFY_RELATION_TOOL],
            tool_choice={"type": "tool", "name": "classify_belief_relation"},
        )
    except anthropic.APIError:
        return BeliefRelationClassification(relation="CONTRADICTS", confidence=0.0, rationale="LLM call failed"), zero_usage

    usage = LlmUsage(
        model=settings.anthropic_extraction_model,
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
    )
    tool_input = _extract_tool_input(message, "classify_belief_relation")
    if tool_input is None:
        return BeliefRelationClassification(relation="CONTRADICTS", confidence=0.0, rationale="No tool response"), usage
    try:
        return BeliefRelationClassification.model_validate(tool_input), usage
    except ValidationError:
        return BeliefRelationClassification(relation="CONTRADICTS", confidence=0.0, rationale="Invalid tool output"), usage

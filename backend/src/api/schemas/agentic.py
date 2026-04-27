"""Pydantic schemas for the agentic SSE wire format.

Defines the event models emitted by ``POST /api/v1/query/agentic`` and the
corresponding request body schema.
"""

from typing import Literal

from pydantic import BaseModel, Field


class RouterStepPayload(BaseModel):
    """Payload emitted when the router node completes."""

    query_type: Literal["factual", "analytical", "multi_hop", "ambiguous"]
    strategy: Literal["dense", "hybrid", "web"]
    duration_ms: int


class GraderStepPayload(BaseModel):
    """Payload emitted when the grader node completes."""

    scores: list[float]
    web_fallback: bool
    duration_ms: int


class CriticStepPayload(BaseModel):
    """Payload emitted when the critic node completes."""

    hallucination_risk: float = Field(ge=0.0, le=1.0)
    reruns: int
    duration_ms: int


class AgentStepEvent(BaseModel):
    """SSE event emitted for each intermediate agent node completion."""

    type: Literal["agent_step"] = "agent_step"
    node: Literal["router", "grader", "critic"]
    # Union resolved at runtime by mutually exclusive required fields.
    # Add Field(discriminator="...") if a future payload type shares field names.
    payload: RouterStepPayload | GraderStepPayload | CriticStepPayload


class AgentQueryRequest(BaseModel):
    """Request body for POST /api/v1/query/agentic."""

    query: str = Field(min_length=1, max_length=2000)
    k: int | None = Field(default=None, ge=1, le=20)
    filters: dict[str, str] | None = None

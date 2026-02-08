"""Pydantic models for API request/response schemas."""

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Part 1: Risk Assessment
# ---------------------------------------------------------------------------

class AssessmentRequest(BaseModel):
    patient_id: str = Field(..., description="Patient ID (e.g., PT-101)", examples=["PT-101"])


class GuidelineCitation(BaseModel):
    recommendation_id: str = ""
    text: str = ""
    page: Optional[str] = None


class AssessmentResponse(BaseModel):
    patient_id: str
    patient_name: str = ""
    risk_level: str = ""
    recommended_action: str = ""
    suspected_cancers: list[str] = []
    reasoning: str = ""
    guideline_citations: list[dict] = []
    additional_notes: str = ""
    retrieved_chunks: list[dict] = []
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Part 2: Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Client-generated session ID")
    message: str = Field(..., description="User's question about NG12 guidelines")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")


class ChatCitation(BaseModel):
    source: str = "NG12 PDF"
    page: int = 0
    chunk_id: str = ""
    excerpt: str = ""
    relevance_score: float = 0.0


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[dict] = []


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[dict] = []


class PatientSummary(BaseModel):
    patient_id: str
    name: str
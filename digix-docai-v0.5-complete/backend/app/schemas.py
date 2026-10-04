from typing import Any
from pydantic import BaseModel, Field

class FieldStatus(BaseModel):
    status: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    evidence: str | None = None

class DetectedCandidate(BaseModel):
    value: Any
    normalized: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    evidence: str
    line_no: int | None = None
    currency: str | None = None

class DocumentAnalysis(BaseModel):
    document_type: str
    filename: str
    provider: str | None = None
    document_date: str | None = None
    due_date: str | None = None
    amount: float | None = None
    currency: str | None = None
    summary: str
    actions: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    ocr_quality: float = Field(ge=0.0, le=1.0)
    extraction_completeness: float = Field(ge=0.0, le=1.0)
    extracted_fields: dict[str, Any]
    field_status: dict[str, FieldStatus]
    detected_candidates: dict[str, list[DetectedCandidate]] = Field(default_factory=dict)
    document_id: str | None = None
    content_type: str | None = None
    file_size_bytes: int = 0
    processing_time_ms: int = 0
    ocr_word_count: int = 0
    ocr_line_count: int = 0
    extracted_count: int = 0
    target_field_count: int = 0
    candidate_count: int = 0
    raw_text: str = ""

class QuestionRequest(BaseModel):
    document_id: str
    question: str

class QuestionAnswer(BaseModel):
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    grounded: bool
    evidence: list[str]

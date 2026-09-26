from typing import Any
from pydantic import BaseModel, Field

class FieldStatus(BaseModel):
    status: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    evidence: str | None = None

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
    document_id: str | None = None

class QuestionRequest(BaseModel):
    document_id: str
    question: str

class QuestionAnswer(BaseModel):
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    grounded: bool
    evidence: list[str]

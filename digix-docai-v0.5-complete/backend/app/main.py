from uuid import uuid4
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .document_service import analyze
from .ocr_service import extract_document
from .qa_service import answer_question
from .schemas import DocumentAnalysis, QuestionAnswer, QuestionRequest

app = FastAPI(title="DigiX DocAI API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED = {"application/pdf", "image/png", "image/jpeg"}
DOCUMENTS = {}

@app.get("/health")
def health():
    return {"status": "ok", "service": "digix-docai", "version": "0.5.0"}

@app.post("/api/v1/documents/analyze", response_model=DocumentAnalysis)
async def analyze_document(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED:
        raise HTTPException(415, "Only PDF, JPG and PNG files are supported.")

    data = await file.read()
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Maximum file size is {settings.max_upload_mb} MB.")

    try:
        filename = file.filename or "document"
        content_type = file.content_type or ""
        ocr = extract_document(filename, content_type, data)

        result = analyze(
            filename,
            content_type,
            data,
            text_override=ocr.text,
            words=ocr.words,
            ocr_quality=ocr.quality,
        )

        document_id = str(uuid4())
        result.document_id = document_id
        DOCUMENTS[document_id] = {
            "text": ocr.text,
            "fields": result.extracted_fields,
            "field_status": result.field_status,
        }
        return result

    except Exception as exc:
        print("PROCESSING ERROR:", repr(exc))
        raise HTTPException(422, "The document could not be processed.")

@app.post("/api/v1/documents/ask", response_model=QuestionAnswer)
def ask_document(req: QuestionRequest):
    if len(req.question.strip()) < 2:
        raise HTTPException(400, "Please enter a question.")

    doc = DOCUMENTS.get(req.document_id)
    if not doc:
        raise HTTPException(404, "Document session not found. Analyze the document again.")

    answer, confidence, grounded, evidence = answer_question(
        req.question,
        doc["text"],
        doc["fields"],
        doc["field_status"],
    )

    return QuestionAnswer(
        answer=answer,
        confidence=confidence,
        grounded=grounded,
        evidence=evidence,
    )

from uuid import uuid4
from fastapi import FastAPI,File,UploadFile,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .document_service import analyze
from .ocr_service import extract_text
from .qa_service import answer_question
from .schemas import DocumentAnalysis,QuestionRequest,QuestionAnswer
app=FastAPI(title="DigiX DocAI API",version="0.3.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
ALLOWED={"application/pdf","image/png","image/jpeg"}; DOCUMENTS={}
@app.get("/health")
def health():return {"status":"ok","service":"digix-docai","version":"0.3.0"}
@app.post("/api/v1/documents/analyze",response_model=DocumentAnalysis)
async def analyze_document(file:UploadFile=File(...)):
    if file.content_type not in ALLOWED:raise HTTPException(415,"Only PDF, JPG and PNG files are supported.")
    data=await file.read()
    if not data:raise HTTPException(400,"The uploaded file is empty.")
    if len(data)>settings.max_upload_mb*1024*1024:raise HTTPException(413,f"Maximum file size is {settings.max_upload_mb} MB.")
    try:
        text=extract_text(file.filename or "document",file.content_type or "",data)
        result=analyze(file.filename or "document",file.content_type or "",data,text_override=text)
        did=str(uuid4()); result.document_id=did
        DOCUMENTS[did]={"text":text,"fields":result.extracted_fields}
        return result
    except Exception as e:
        print("PROCESSING ERROR:",repr(e)); raise HTTPException(422,"The document could not be processed.")
@app.post("/api/v1/documents/ask",response_model=QuestionAnswer)
def ask_document(req:QuestionRequest):
    if len(req.question.strip())<2:raise HTTPException(400,"Please enter a question.")
    doc=DOCUMENTS.get(req.document_id)
    if not doc:raise HTTPException(404,"Document session not found. Analyze the document again.")
    a,c,g,e=answer_question(req.question,doc["text"],doc["fields"])
    return QuestionAnswer(answer=a,confidence=c,grounded=g,evidence=e)

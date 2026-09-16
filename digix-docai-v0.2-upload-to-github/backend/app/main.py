from fastapi import FastAPI,File,UploadFile,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .document_service import analyze
from .schemas import DocumentAnalysis
app=FastAPI(title="DigiX DocAI API",version="0.2.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
ALLOWED={"application/pdf","image/png","image/jpeg"}
@app.get("/health")
def health(): return {"status":"ok","service":"digix-docai","version":"0.2.0"}
@app.post("/api/v1/documents/analyze",response_model=DocumentAnalysis)
async def analyze_document(file:UploadFile=File(...)):
    if file.content_type not in ALLOWED: raise HTTPException(415,"Only PDF, JPG and PNG files are supported.")
    data=await file.read()
    if not data: raise HTTPException(400,"The uploaded file is empty.")
    if len(data)>settings.max_upload_mb*1024*1024: raise HTTPException(413,f"Maximum file size is {settings.max_upload_mb} MB.")
    return analyze(file.filename or "document",file.content_type or "",data)

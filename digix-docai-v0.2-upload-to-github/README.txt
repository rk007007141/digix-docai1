DigiX DocAI v0.3.0 — Ask Your Document
Replace schemas.py, main.py, App.tsx; add qa_service.py.
Apply the tiny document_service.py change in PATCH_document_service.txt.
Append ADD_TO_CSS.txt to the end of your existing frontend CSS file.
Then git pull and restart backend + frontend.
Health endpoint must report 0.3.0.
Q&A is local/grounded: no paid AI key yet. It answers extracted fields or matching OCR evidence and says not found when unsupported.
Document sessions are in memory and reset when backend restarts.

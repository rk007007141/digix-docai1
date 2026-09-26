# DigiX DocAI v0.5.0

Complete local-first Document Intelligence MVP.

## What v0.5 changes

- OCR words keep coordinates and confidence.
- OCR words are rebuilt into visual lines.
- Bill fields use label/value layout matching plus validated text fallbacks.
- Document-type confidence, OCR quality and extraction completeness are separate.
- Every target field has its own extracted/not-reliably-read status.
- Ask Your Document returns a known field only when it was reliably extracted.
- Missing fields are not replaced with unrelated OCR lines.
- No paid AI API is required in this version.

## Stack

Frontend: React + TypeScript + Vite  
Backend: FastAPI  
OCR: Tesseract/pytesseract  
PDF text: pypdf

## Windows start

Tesseract default:
`C:\Program Files\Tesseract-OCR\tesseract.exe`

Backend:

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Health:
`http://127.0.0.1:8000/health`

Frontend, in another CMD:

```cmd
cd frontend
npm install
npm run dev
```

Open:
`http://localhost:5173`

For your existing GitHub project, replace the backend and frontend source files with the files in this package. Do not upload `.venv` or `node_modules`.

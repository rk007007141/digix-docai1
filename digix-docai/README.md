# DigiX DocAI

**Upload anything. Understand it. Act on it.**

A runnable MVP for document intelligence: upload a PDF/JPG/PNG, classify it, extract useful fields, receive a summary and suggested actions.

## Stack
- React + TypeScript + Vite
- Python + FastAPI
- Local/mock analysis first (no paid AI key required)
- Supabase-ready configuration
- GitHub Actions CI

## Run locally

### Backend
```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Security
Never commit `.env`, API keys, Supabase service-role keys, or customer documents.
The MVP processes uploads in memory and does not persist originals.

## Next production steps
1. Supabase Auth + private Storage + RLS
2. Production OCR/document parser
3. Server-side LLM provider gateway
4. History, document chat and reminders
5. Capacitor Android packaging
6. Subscription/usage limits

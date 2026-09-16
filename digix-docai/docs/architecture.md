# Architecture

## MVP
Browser / future Capacitor Android app
→ React + TypeScript
→ HTTPS REST
→ FastAPI
→ document processor
→ structured JSON response

The current provider is deliberately local/mock so the project runs without paid credentials.

## Production target
React/Capacitor → FastAPI API → authentication/authorization → private document storage → extraction/OCR → AI gateway → structured result → PostgreSQL.

Supabase is the planned first-stage platform for Auth, PostgreSQL and private Storage.

## Privacy
- API keys remain server-side.
- Original documents should use private object storage.
- RLS isolates user metadata.
- Prefer deleting originals after processing when the user does not request storage.
- Record AI model and processing cost per result.

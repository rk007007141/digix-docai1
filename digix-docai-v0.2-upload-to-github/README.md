# DigiX DocAI v0.2
Upload anything. Understand it. Act on it.

## Run backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

## Run frontend
cd frontend
npm install
npm run dev

## Image OCR on Windows
Install the free Tesseract OCR executable and ensure `tesseract.exe` is on PATH.
Then restart the backend. Text PDFs work without Tesseract.

import io
import re
from pathlib import Path
from pypdf import PdfReader
from .schemas import DocumentAnalysis

def _pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)[:30000]
    except Exception:
        return ""

def _classify(name: str, text: str) -> str:
    s = (name + " " + text).lower()
    if "invoice" in s: return "invoice"
    if "receipt" in s: return "receipt"
    if any(x in s for x in ["electricity", "bill amount", "due date", "utility"]): return "bill"
    if "notice" in s: return "notice"
    return "generic_document"

def _money(text: str):
    patterns = [
        r"(?:₹|INR|Rs\.?)\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        r"(?:total|amount due|bill amount)\s*[:\-]?\s*(?:₹|INR|Rs\.?)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)"
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try: return float(m.group(1).replace(",", ""))
            except ValueError: pass
    return None

def _date(label: str, text: str):
    m = re.search(label + r"\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})", text, re.I)
    return m.group(1) if m else None

def analyze(filename: str, content_type: str, data: bytes) -> DocumentAnalysis:
    text = _pdf_text(data) if content_type == "application/pdf" or filename.lower().endswith(".pdf") else ""
    dtype = _classify(filename, text)
    amount = _money(text)
    due = _date("due date", text)
    doc_date = _date("(?:bill date|invoice date|date)", text)

    if text:
        clean = " ".join(text.split())
        summary = f"This {dtype.replace('_',' ')} was processed successfully. " + clean[:260]
        confidence = 0.82
    else:
        summary = f"{Path(filename).name} is a {dtype.replace('_',' ')}. Image OCR/vision is the next AI integration step."
        confidence = 0.55

    actions = ["Review the extracted information for accuracy"]
    if due: actions.append(f"Take required action before {due}")
    if amount is not None: actions.append("Compare this amount with previous documents")
    actions.append("Save the analysis only if you want it in your history")

    currency = "INR" if any(x in text for x in ["₹", "INR", "Rs"]) else None
    fields = {
        "filename": filename,
        "document_type": dtype,
        "document_date": doc_date,
        "due_date": due,
        "amount": amount,
        "currency": currency,
    }
    return DocumentAnalysis(
        document_type=dtype, filename=filename, document_date=doc_date,
        due_date=due, amount=amount, currency=currency, summary=summary,
        actions=actions, confidence=confidence, extracted_fields=fields
    )

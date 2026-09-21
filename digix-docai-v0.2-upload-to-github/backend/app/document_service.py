import re
from pathlib import Path
from .ocr_service import extract_text
from .schemas import DocumentAnalysis

ELECTRICITY_TERMS=("electricity","electric power","power company","electric supply","consumer number","consumer no","meter no","meter number","units consumed","kwh","bill amount","electric bill","gujranwala electric power company","gepco")

def classify(name,text):
    s=(name+" "+text).lower()
    if any(x in s for x in ELECTRICITY_TERMS): return "electricity_bill"
    if any(x in s for x in ("tax invoice","gst invoice","invoice")): return "invoice"
    if any(x in s for x in ("receipt","payment received")): return "receipt"
    if any(x in s for x in ("insurance","policy number","premium")): return "insurance_document"
    if any(x in s for x in ("bank statement","account statement")): return "bank_statement"
    if any(x in s for x in ("school notice","principal","student notice")): return "school_notice"
    if "notice" in s: return "notice"
    return "generic_document"

def match(pattern,text):
    m=re.search(pattern,text,re.I|re.M)
    return m.group(1).strip() if m else None

def amount(text):
    for p in (r"(?:amount\s*due|bill\s*amount|net\s*amount|payable\s*amount|total\s*amount|total)\s*[:\-]?\s*(?:PKR|Rs\.?|₹|INR)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",r"(?:PKR|Rs\.?|₹|INR)\s*([0-9][0-9,]*(?:\.\d{1,2})?)"):
        v=match(p,text)
        if v:
            try:return float(v.replace(",",""))
            except ValueError:pass
    return None

def date(label,text):
    return match(label+r"\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2})",text)

def provider(text):
    s=text.lower()
    if "gujranwala electric power company" in s or re.search(r"\bgepco\b",s): return "Gujranwala Electric Power Company"
    return next((x for x in ("MSEDCL","Adani Electricity","Tata Power","Reliance","Torrent Power") if x.lower() in s),None)

def consumer(text):
    for p in (r"(?:consumer|account)\s*(?:no|number|#)?\s*[:\-]?\s*([A-Z0-9\-]{5,})",r"(?:reference|ref)\s*(?:no|number|#)?\s*[:\-]?\s*([A-Z0-9\-]{5,})"):
        v=match(p,text)
        if v:return v
    return None

def analyze(filename,content_type,data):
    text=extract_text(filename,content_type,data); readable=bool(text.strip())
    dtype=classify(filename,text); prov=provider(text); amt=amount(text)
    due=date(r"(?:due\s*date|pay\s*by|last\s*date)",text)
    docdate=date(r"(?:bill\s*date|invoice\s*date|issue\s*date|date)",text)
    cons=consumer(text)
    currency="INR" if any(x in text for x in ("₹","INR")) else ("PKR" if re.search(r"\bPKR\b|\bRs\.?",text,re.I) or prov=="Gujranwala Electric Power Company" else None)
    summary=(f"This appears to be a {dtype.replace('_',' ')}. Important details were extracted automatically." if readable else f"{Path(filename).name} could not be read as text. The document may be unreadable or require scanned-PDF OCR.")
    actions=["Review the extracted information for accuracy"]
    if due:actions.append(f"Take required action before {due}")
    if amt is not None:actions.append("Compare this amount with previous documents")
    actions.append("Save the analysis only if you want it in your history")
    fields={"filename":filename,"document_type":dtype,"provider":prov,"consumer_number":cons,"document_date":docdate,"due_date":due,"amount":amt,"currency":currency}
    confidence=.35 if not readable else (.90 if dtype!="generic_document" else .70)
    return DocumentAnalysis(document_type=dtype,filename=filename,provider=prov,document_date=docdate,due_date=due,amount=amt,currency=currency,summary=summary,actions=actions,confidence=confidence,extracted_fields=fields)

import re
from pathlib import Path
from .ocr_service import extract_text
from .schemas import DocumentAnalysis

def classify(name,text):
    s=(name+" "+text).lower()
    if any(x in s for x in ["electricity","consumer number","consumer no","bill amount"]): return "electricity_bill"
    if any(x in s for x in ["tax invoice","gst invoice","invoice"]): return "invoice"
    if any(x in s for x in ["receipt","payment received"]): return "receipt"
    if any(x in s for x in ["insurance","policy number","premium"]): return "insurance_document"
    if any(x in s for x in ["bank statement","account statement"]): return "bank_statement"
    if any(x in s for x in ["school notice","principal","student notice"]): return "school_notice"
    if "notice" in s: return "notice"
    return "generic_document"

def match(pattern,text):
    m=re.search(pattern,text,re.I)
    return m.group(1) if m else None

def amount(text):
    v=match(r"(?:amount due|bill amount|net amount|total)\s*[:\-]?\s*(?:₹|INR|Rs\.?)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",text)
    if not v: v=match(r"(?:₹|INR|Rs\.?)\s*([0-9][0-9,]*(?:\.\d{1,2})?)",text)
    try:return float(v.replace(",","")) if v else None
    except:return None

def date(label,text):
    return match(label+r"\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})",text)

def analyze(filename,content_type,data):
    text=extract_text(filename,content_type,data)
    dtype=classify(filename,text)
    amt=amount(text)
    due=date("due date",text)
    docdate=date(r"(?:bill date|invoice date|date)",text)
    provider=next((x for x in ["MSEDCL","Adani Electricity","Tata Power","Reliance","Torrent Power"] if x.lower() in text.lower()),None)
    consumer=match(r"(?:consumer|account)\s*(?:no|number|#)?\s*[:\-]?\s*([A-Z0-9-]{6,})",text)
    currency="INR" if any(x in text for x in ["₹","INR","Rs"]) else None
    readable=bool(text.strip())
    summary=(f"This appears to be a {dtype.replace('_',' ')}. Important details were extracted automatically."
             if readable else f"{Path(filename).name} could not be read as text. Install Tesseract OCR for image analysis.")
    actions=["Review the extracted information for accuracy"]
    if due: actions.append(f"Take required action before {due}")
    if amt is not None: actions.append("Compare this amount with previous documents")
    actions.append("Save the analysis only if you want it in your history")
    fields={"filename":filename,"document_type":dtype,"provider":provider,"consumer_number":consumer,
            "document_date":docdate,"due_date":due,"amount":amt,"currency":currency}
    return DocumentAnalysis(document_type=dtype,filename=filename,provider=provider,document_date=docdate,
      due_date=due,amount=amt,currency=currency,summary=summary,actions=actions,
      confidence=(.90 if readable and dtype!="generic_document" else .70 if readable else .35),
      extracted_fields=fields)

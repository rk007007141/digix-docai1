import re
from pathlib import Path
from .ocr_service import extract_text
from .schemas import DocumentAnalysis

ELECTRICITY_TERMS=("electricity","electric power","power company","electric supply","consumer number","consumer no","meter no","meter number","units consumed","kwh","bill amount","electric bill","gujranwala electric power company","gepco")

def clean(v):
    return re.sub(r"\s+"," ",v).strip(" :|-") if v else None

def first(patterns,text):
    for p in patterns:
        m=re.search(p,text,re.I|re.M)
        if m:return clean(m.group(1))
    return None

def classify(name,text):
    s=(name+" "+text).lower()
    if any(x in s for x in ELECTRICITY_TERMS):return "electricity_bill"
    if any(x in s for x in ("tax invoice","gst invoice","invoice")):return "invoice"
    if any(x in s for x in ("receipt","payment received")):return "receipt"
    if any(x in s for x in ("insurance","policy number","premium")):return "insurance_document"
    if any(x in s for x in ("bank statement","account statement")):return "bank_statement"
    if any(x in s for x in ("school notice","principal","student notice")):return "school_notice"
    if "notice" in s:return "notice"
    return "generic_document"

def provider(text):
    s=text.lower()
    if "gujranwala electric power company" in s or re.search(r"\bgepco\b",s):return "Gujranwala Electric Power Company"
    return next((x for x in ("MSEDCL","Adani Electricity","Tata Power","Reliance","Torrent Power") if x.lower() in s),None)

def number_field(labels,text,minlen=4):
    label="|".join(labels)
    return first([
        rf"(?:{label})\s*(?:no|number|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/ ]{{{minlen},24}})",
        rf"(?:{label})\s*[:\-]?\s*([0-9][0-9\- ]{{{minlen},24}})"
    ],text)

def date_field(labels,text):
    label="|".join(labels)
    return first([
        rf"(?:{label})\s*[:\-]?\s*(\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}})",
        rf"(?:{label})\s*[:\-]?\s*(\d{{4}}-\d{{2}}-\d{{2}})"
    ],text)

def money(text):
    v=first([
        r"(?:amount\s*due|bill\s*amount|payable\s*amount|net\s*amount|total\s*amount|payable|total)\s*[:\-]?\s*(?:PKR|Rs\.?|₹|INR)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        r"(?:PKR|Rs\.?|₹|INR)\s*([0-9][0-9,]*(?:\.\d{1,2})?)"
    ],text)
    try:return float(v.replace(",","")) if v else None
    except ValueError:return None

def numeric(labels,text):
    label="|".join(labels)
    v=first([rf"(?:{label})\s*[:\-]?\s*([0-9][0-9,.]*)"],text)
    return v

def analyze(filename,content_type,data):
    text=extract_text(filename,content_type,data)
    readable=bool(text.strip())
    dtype=classify(filename,text)
    prov=provider(text)
    amt=money(text)
    due=date_field(("due date","pay by","last date"),text)
    bill_date=date_field(("bill date","invoice date","issue date"),text)
    cons=number_field(("consumer","consumer id","account"),text)
    reference=number_field(("reference","ref"),text)
    meter=number_field(("meter","meter id"),text)
    bill_month=first([r"(?:bill\s*month|billing\s*month)\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{4}|\d{1,2}[/-]\d{4})"],text)
    units=numeric(("units consumed","units","kwh"),text)
    current=numeric(("current reading","present reading"),text)
    previous=numeric(("previous reading","prev reading"),text)
    currency="INR" if any(x in text for x in ("₹","INR")) else ("PKR" if re.search(r"\bPKR\b|\bRs\.?",text,re.I) or prov=="Gujranwala Electric Power Company" else None)

    fields={"filename":filename,"document_type":dtype,"provider":prov,"consumer_number":cons,
            "reference_number":reference,"meter_number":meter,"bill_month":bill_month,
            "document_date":bill_date,"due_date":due,"amount":amt,"currency":currency,
            "units_consumed":units,"current_reading":current,"previous_reading":previous}
    fields={k:v for k,v in fields.items() if v is not None}

    detected=sum(v is not None for v in (prov,cons,reference,meter,bill_month,bill_date,due,amt,units,current,previous))
    if not readable:confidence=.35
    elif dtype=="generic_document":confidence=.70
    else:confidence=min(.97,.86+min(detected,5)*.02)

    summary=(f"This appears to be a {dtype.replace('_',' ')}. {detected} key field(s) were detected automatically."
             if readable else f"{Path(filename).name} could not be read as text. The document may be unreadable or require scanned-PDF OCR.")
    actions=["Review the extracted information for accuracy"]
    if due:actions.append(f"Take required action before {due}")
    if amt is not None:actions.append("Verify the payable amount before payment")
    if cons or reference:actions.append("Use the detected consumer/reference number when verifying the bill")
    actions.append("Save the analysis only if you want it in your history")

    return DocumentAnalysis(document_type=dtype,filename=filename,provider=prov,document_date=bill_date,
        due_date=due,amount=amt,currency=currency,summary=summary,actions=actions,
        confidence=confidence,extracted_fields=fields)

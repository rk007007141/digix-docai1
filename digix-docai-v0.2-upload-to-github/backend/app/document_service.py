import re
from pathlib import Path
from .ocr_service import extract_text
from .schemas import DocumentAnalysis
BAD={"bill","consumer","number","meter","reference","account","date","amount","reading","units","month","due","from","rom","www","wwnerece"}
def clean(v): return re.sub(r"\s+"," ",v).strip(" :|-") if v else None
def first(ps,t):
 for p in ps:
  m=re.search(p,t,re.I|re.M)
  if m:return clean(m.group(1))
def classify(n,t):
 s=(n+" "+t).lower()
 if any(x in s for x in ("electricity","electric power","power company","gepco","gujranwala","kwh")):return "electricity_bill"
 if "invoice" in s:return "invoice"
 if "receipt" in s:return "receipt"
 if "insurance" in s:return "insurance_document"
 if "bank statement" in s:return "bank_statement"
 if "notice" in s:return "notice"
 return "generic_document"
def provider(t):
 s=t.lower()
 if "gujranwala electric power company" in s or re.search(r"\bgepco\b",s):return "Gujranwala Electric Power Company"
 for x in ("MSEDCL","Adani Electricity","Tata Power","Reliance","Torrent Power"):
  if x.lower() in s:return x
def ident(labels,t,digits=4):
 L="|".join(re.escape(x) for x in labels)
 for p in (rf"(?:{L})\s*(?:no\.?|number|#|id)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{{3,29}})",rf"(?:{L}).{{0,10}}?\b([0-9][0-9\-]{{3,29}})\b"):
  for m in re.finditer(p,t,re.I):
   v=clean(m.group(1)); low=v.lower()
   ds=sum(c.isdigit() for c in v); an=sum(c.isalnum() for c in v)
   if ds>=digits and (not an or ds/an>=.45) and not any(re.search(rf"\b{re.escape(w)}\b",low) for w in BAD):return v
def date(labels,t):
 L="|".join(re.escape(x) for x in labels)
 return first([rf"(?:{L})\s*[:\-]?\s*(\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}})",rf"(?:{L})\s*[:\-]?\s*(\d{{4}}-\d{{1,2}}-\d{{1,2}})"],t)
def amount(t):
 for p in (r"(?:amount\s*due|bill\s*amount|payable\s*amount|net\s*amount|total\s*amount|grand\s*total|amount\s*payable|payable|total)\s*[:\-]?\s*(?:PKR|Rs\.?|₹|INR)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",r"(?:PKR|Rs\.?|₹|INR)\s*([0-9][0-9,]*(?:\.\d{1,2})?)"):
  m=re.search(p,t,re.I)
  if m:
   try:
    n=float(m.group(1).replace(",",""))
    if 0<n<100000000:return n
   except:pass
def num(labels,t):
 L="|".join(re.escape(x) for x in labels)
 return first([rf"(?:{L})\s*[:\-]?\s*([0-9][0-9,.]*)"],t)
def analyze(filename,content_type,data,text_override=None):
 t=text_override if text_override is not None else extract_text(filename,content_type,data); readable=bool(t.strip())
 typ=classify(filename,t); prov=provider(t); amt=amount(t); due=date(("due date","pay by","last date"),t); dd=date(("bill date","invoice date","issue date"),t)
 cons=ident(("consumer number","consumer no","consumer id","consumer","account number"),t,5); ref=ident(("reference number","reference no","ref no"),t,5); meter=ident(("meter number","meter no","meter id"),t,4)
 month=first([r"(?:bill\s*month|billing\s*month)\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{4}|\d{1,2}[/-]\d{4})"],t)
 units=num(("units consumed","consumption","units","kwh"),t); cur=num(("current reading","present reading"),t); prev=num(("previous reading","prev reading"),t)
 curr="INR" if re.search(r"\bINR\b|₹",t,re.I) else ("PKR" if re.search(r"\bPKR\b|\bRs\.?",t,re.I) or prov=="Gujranwala Electric Power Company" else None)
 f={"filename":filename,"document_type":typ,"provider":prov,"consumer_number":cons,"reference_number":ref,"meter_number":meter,"bill_month":month,"document_date":dd,"due_date":due,"amount":amt,"currency":curr,"units_consumed":units,"current_reading":cur,"previous_reading":prev}
 f={k:v for k,v in f.items() if v not in (None,"")}; detected=sum(v not in (None,"") for v in (prov,cons,ref,meter,month,dd,due,amt,units,cur,prev))
 conf=.35 if not readable else (.70 if typ=="generic_document" else min(.97,.84+min(detected,6)*.02))
 summary=f"This appears to be an {typ.replace('_',' ')}. {detected} key field(s) passed validation and were extracted." if readable else f"{Path(filename).name} could not be read as text."
 acts=["Review the extracted information for accuracy"]
 if due:acts.append(f"Take required action before {due}")
 if amt is not None:acts.append("Verify the payable amount before payment")
 if cons or ref:acts.append("Use the validated consumer/reference number when verifying the document")
 acts.append("Ask questions about this document below")
 return DocumentAnalysis(document_type=typ,filename=filename,provider=prov,document_date=dd,due_date=due,amount=amt,currency=curr,summary=summary,actions=acts,confidence=conf,extracted_fields=f)

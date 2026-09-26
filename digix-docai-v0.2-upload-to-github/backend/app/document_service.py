import re
from pathlib import Path
from .schemas import DocumentAnalysis
def first(ps,t):
 for p in ps:
  m=re.search(p,t,re.I|re.M)
  if m:return re.sub(r"\s+"," ",m.group(1)).strip(" :-|")
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
 if re.search(r"gujranwala\s+electric\s+power\s+company|\bgepco\b",t,re.I):return "Gujranwala Electric Power Company"
 for x in ("MSEDCL","Adani Electricity","Tata Power","Reliance","Torrent Power"):
  if x.lower() in t.lower():return x
def valid_id(v):
 if not v:return None
 v=v.strip(); digits=sum(c.isdigit() for c in v); al=sum(c.isalnum() for c in v)
 return v if digits>=4 and al and digits/al>=.5 and len(v)<=30 else None
def ident(labels,t):
 L="|".join(re.escape(x) for x in labels)
 for m in re.finditer(rf"(?:{L})\s*(?:no\.?|number|#|id)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{{3,29}})",t,re.I):
  v=valid_id(m.group(1))
  if v:return v
def date(labels,t):
 L="|".join(re.escape(x) for x in labels)
 return first([rf"(?:{L})\s*[:\-]?\s*(\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}})",rf"(?:{L})\s*[:\-]?\s*(\d{{4}}-\d{{1,2}}-\d{{1,2}})"],t)
def money(labels,t):
 L="|".join(re.escape(x) for x in labels)
 v=first([rf"(?:{L})\s*[:\-]?\s*(?:PKR|Rs\.?|₹|INR)?\s*([0-9][0-9,]*(?:\.\d{{1,2}})?)"],t)
 try:return float(v.replace(",","")) if v else None
 except:return None
def num(labels,t):
 L="|".join(re.escape(x) for x in labels)
 return first([rf"(?:{L})\s*[:\-]?\s*([0-9][0-9,.]*)"],t)
def add(fields,status,k,v,source="label-value",conf=.88):
 if v not in (None,""):
  fields[k]=v;status[k]={"status":"extracted","confidence":conf,"source":source}
 else:status[k]={"status":"not_reliably_read","confidence":0.0,"source":source}
def analyze(filename,content_type,data,text_override=None,words=None):
 t=text_override or "";typ=classify(filename,t);p=provider(t);fields={};status={}
 add(fields,status,"filename",filename,"upload",1);add(fields,status,"document_type",typ,"classifier",.9 if typ!="generic_document" else .7);add(fields,status,"provider",p,"OCR",.95 if p else 0)
 add(fields,status,"consumer_number",ident(("consumer number","consumer no","consumer id","consumer","account number"),t))
 add(fields,status,"reference_number",ident(("reference number","reference no","ref no"),t))
 add(fields,status,"meter_number",ident(("meter number","meter no","meter id"),t))
 add(fields,status,"bill_month",first([r"(?:bill\s*month|billing\s*month)\s*[:\-]?\s*([A-Za-z]{3,9}\s+\d{4}|\d{1,2}[/-]\d{4})"],t))
 dd=date(("bill date","invoice date","issue date"),t);due=date(("due date","pay by","last date"),t)
 add(fields,status,"document_date",dd);add(fields,status,"due_date",due)
 add(fields,status,"units_consumed",num(("units consumed","consumption","units","kwh"),t))
 add(fields,status,"previous_reading",num(("previous reading","prev reading"),t));add(fields,status,"current_reading",num(("current reading","present reading"),t))
 add(fields,status,"current_charges",money(("current charges","current bill","current amount"),t))
 add(fields,status,"taxes_surcharges",money(("taxes","surcharge","tax","gst"),t))
 add(fields,status,"arrears",money(("arrears","previous balance","outstanding"),t))
 before=money(("amount before due date","payable within due date","amount due","bill amount","total amount"),t)
 after=money(("amount after due date","payable after due date","late payment amount"),t)
 add(fields,status,"amount_before_due",before);add(fields,status,"amount_after_due",after)
 currency="INR" if re.search(r"\bINR\b|₹",t,re.I) else ("PKR" if re.search(r"\bPKR\b|\bRs\.?",t,re.I) or p else None);add(fields,status,"currency",currency,"currency detection",.95 if currency else 0)
 extracted=sum(1 for k,v in status.items() if v["status"]=="extracted" and k not in ("filename","document_type"))
 conf=min(.97,.72+.03*min(extracted,7)) if t.strip() else .35
 summary=f"{typ.replace('_',' ').title()} detected. {extracted} information field(s) were reliably extracted; unreadable fields are explicitly marked instead of guessed."
 actions=["Review extracted values against the original document","Ask questions about the document below"]
 if due:actions.append(f"Take required action before {due}")
 return DocumentAnalysis(document_type=typ,filename=filename,provider=p,document_date=dd,due_date=due,amount=before,currency=currency,summary=summary,actions=actions,confidence=conf,extracted_fields=fields,field_status=status)

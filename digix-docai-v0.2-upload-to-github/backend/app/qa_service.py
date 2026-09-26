import re
ALIASES={"amount":("amount","total","payable"),"due_date":("due","deadline","last date"),"document_date":("bill date","invoice date","issue date"),"provider":("provider","company","issuer"),"consumer_number":("consumer","account number"),"reference_number":("reference","ref number"),"meter_number":("meter","meter number"),"bill_month":("bill month","billing month"),"units_consumed":("units","consumption","kwh"),"current_reading":("current reading","present reading"),"previous_reading":("previous reading","prev reading")}
STOP={"what","when","where","which","who","why","how","is","are","the","a","an","of","to","for","in","on","my","this","document","bill","please","tell","me"}
def answer_question(q,t,f):
 q=q.lower()
 for k,a in ALIASES.items():
  if any(x in q for x in a) and f.get(k) not in (None,""):
   v=f[k]
   if k=="amount" and f.get("currency"):v=f"{f['currency']} {v}"
   return f"{k.replace('_',' ').title()}: {v}",1.0,True,[str(v)]
 terms=[w for w in re.findall(r"[a-z0-9]+",q) if len(w)>2 and w not in STOP]; lines=[re.sub(r"\s+"," ",x).strip() for x in t.splitlines() if len(x.strip())>3]
 s=sorted([(sum(z in x.lower() for z in terms),len(x),x) for x in lines if any(z in x.lower() for z in terms)],key=lambda x:(-x[0],x[1])); ev=[]
 for _,_,x in s:
  if x not in ev:ev.append(x)
  if len(ev)==3:break
 if not ev:return "I could not reliably find that information in the document.",0.0,False,[]
 return " ".join(ev),min(.90,.55+.10*s[0][0]),True,ev

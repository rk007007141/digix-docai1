import re
STOP={"what","when","where","which","who","why","how","is","are","the","a","an","of","to","for","in","on","my","this","document","bill","please","tell","me"}
ALIASES={"amount":("amount","total","payable","payment"),"due_date":("due","deadline","last date","pay by"),"provider":("provider","company","issuer"),"consumer_number":("consumer","account number"),"reference_number":("reference","ref number"),"meter_number":("meter","meter number"),"bill_month":("bill month","billing month"),"units_consumed":("units","consumption","kwh")}
def answer_question(question,text,fields):
    q=question.lower()
    for key,aliases in ALIASES.items():
        if any(a in q for a in aliases) and fields.get(key) not in (None,""):
            v=fields[key]
            if key=="amount" and fields.get("currency"):v=f"{fields['currency']} {v}"
            return f"{key.replace('_',' ').title()}: {v}",1.0,True,[str(v)]
    terms=[w for w in re.findall(r"[a-z0-9]+",q) if len(w)>2 and w not in STOP]
    lines=[re.sub(r"\s+"," ",x).strip() for x in text.splitlines() if len(x.strip())>3]
    scored=[]
    for line in lines:
        score=sum(t in line.lower() for t in terms)
        if score:scored.append((score,len(line),line))
    scored.sort(key=lambda x:(-x[0],x[1]))
    evidence=[]
    for _,_,line in scored:
        if line not in evidence:evidence.append(line)
        if len(evidence)==3:break
    if not evidence:return "I could not find that information in the document.",0.0,False,[]
    return " ".join(evidence),min(.90,.55+.10*scored[0][0]),True,evidence

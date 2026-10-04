import { useMemo, useState } from "react";

type FieldStatus={status:string;confidence:number;source:string;evidence?:string|null};
type DetectedCandidate={value:unknown;normalized:string;confidence:number;source:string;evidence:string;line_no?:number|null;currency?:string|null};
type Analysis={document_type:string;filename:string;summary:string;confidence:number;ocr_quality:number;extraction_completeness:number;extracted_fields:Record<string,unknown>;field_status:Record<string,FieldStatus>;detected_candidates:Record<string,DetectedCandidate[]>;actions:string[];document_id?:string;content_type?:string|null;file_size_bytes?:number;processing_time_ms?:number;ocr_word_count?:number;ocr_line_count?:number;extracted_count?:number;target_field_count?:number;candidate_count?:number;raw_text?:string};
type Answer={answer:string;confidence:number;grounded:boolean;evidence:string[]};

const API_BASE=import.meta.env.VITE_API_BASE_URL||"http://127.0.0.1:8000";
const PREFERRED=["provider","customer_name","consumer_number","reference_number","meter_number","tariff","bill_month","billing_period","document_date","due_date","units_consumed","previous_reading","current_reading","current_charges","taxes_surcharges","arrears","amount_before_due","amount_after_due","currency"];
const CANDIDATES=["dates","amounts","identifiers","names","measurements"];
const label=(k:string)=>k.replace(/_/g," ");
const pct=(n?:number)=>`${Math.round((n||0)*100)}%`;
const display=(v:unknown)=>v===null||v===undefined||v===""?"—":typeof v==="object"?JSON.stringify(v):String(v);
const size=(b?:number)=>!b?"0 KB":b<1024?`${b} B`:b<1048576?`${(b/1024).toFixed(1)} KB`:`${(b/1048576).toFixed(2)} MB`;

export default function App(){
 const[file,setFile]=useState<File|null>(null),[result,setResult]=useState<Analysis|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(""),[question,setQuestion]=useState(""),[answer,setAnswer]=useState<Answer|null>(null),[asking,setAsking]=useState(false);

 const fields=useMemo(()=>{if(!result)return[];const keys=new Set([...PREFERRED,...Object.keys(result.field_status||{}),...Object.keys(result.extracted_fields||{})]);keys.delete("filename");keys.delete("document_type");return [...PREFERRED.filter(k=>keys.has(k)),...[...keys].filter(k=>!PREFERRED.includes(k)).sort()].map(key=>({key,value:result.extracted_fields?.[key],status:result.field_status?.[key]}));},[result]);
 const groups=useMemo(()=>{if(!result)return[];const keys=new Set([...CANDIDATES,...Object.keys(result.detected_candidates||{})]);return [...CANDIDATES.filter(k=>keys.has(k)),...[...keys].filter(k=>!CANDIDATES.includes(k)).sort()].map(key=>({key,items:result.detected_candidates?.[key]||[]})).filter(g=>g.items.length);},[result]);

 async function analyze(){if(!file)return;setBusy(true);setError("");setResult(null);setAnswer(null);const body=new FormData();body.append("file",file);try{const r=await fetch(`${API_BASE}/api/v1/documents/analyze`,{method:"POST",body});if(!r.ok)throw new Error(await r.text());setResult(await r.json())}catch(e){setError(e instanceof Error?e.message:"Unable to connect to backend.")}finally{setBusy(false)}}
 async function ask(){if(!result?.document_id||!question.trim())return;setAsking(true);setError("");setAnswer(null);try{const r=await fetch(`${API_BASE}/api/v1/documents/ask`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({document_id:result.document_id,question})});if(!r.ok)throw new Error(await r.text());setAnswer(await r.json())}catch(e){setError(e instanceof Error?e.message:"Question failed.")}finally{setAsking(false)}}

 return <main>
  <header><b>DigiX <i>DocAI</i></b><span>v0.5.2 · Candidate Intelligence</span></header>
  <section className="hero"><small>DOCUMENT INTELLIGENCE</small><h1>Map what is safe.<br/><em>Show everything useful.</em></h1><p>Confident fields plus all credible OCR dates, amounts, IDs, names and measurements.</p></section>
  <section className="card upload"><h2>Analyze a document</h2><p>PDF, JPG or PNG · maximum 10 MB</p><label className="filePicker"><input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={e=>setFile(e.target.files?.[0]||null)}/>{file?file.name:"Choose document"}</label><button disabled={!file||busy} onClick={analyze}>{busy?"Reading and understanding document…":"Analyze document"}</button>{error&&<p className="error">{error}</p>}</section>

  {result&&<>
   <section className="card">
    <div className="top"><div><small>ANALYSIS</small><h2>{label(result.document_type)}</h2><p className="muted">{result.summary}</p></div><div className="metrics"><div><small>TYPE CONFIDENCE</small><b>{pct(result.confidence)}</b></div><div><small>OCR QUALITY</small><b>{pct(result.ocr_quality)}</b></div><div><small>MAPPED FIELDS</small><b>{pct(result.extraction_completeness)}</b></div></div></div>
    <h3>Document & processing details</h3><div className="metaGrid"><div><small>Filename</small><b>{result.filename}</b></div><div><small>Content type</small><b>{result.content_type||"—"}</b></div><div><small>File size</small><b>{size(result.file_size_bytes)}</b></div><div><small>Processing time</small><b>{result.processing_time_ms??0} ms</b></div><div><small>OCR words / lines</small><b>{result.ocr_word_count??0} / {result.ocr_line_count??0}</b></div><div><small>Mapped fields</small><b>{result.extracted_count??0} / {result.target_field_count??fields.length}</b></div><div><small>OCR candidates</small><b>{result.candidate_count??0}</b></div></div>

    <h3>Mapped document fields</h3><p className="muted">Only values with enough context are assigned to a business field.</p><div className="fieldGrid">{fields.map(({key,value,status})=>{const ok=status?.status==="extracted"&&value!==undefined&&value!==null&&value!=="";return <div className={`field ${ok?"fieldGood":"fieldMissing"}`} key={key}><div className="fieldHead"><small>{label(key)}</small>{ok?<span className="good">✓ {pct(status?.confidence)}</span>:<span className="missing">Not reliably mapped</span>}</div><b>{display(value)}</b><div className="fieldMeta"><span>Source: {status?.source||"none"}</span><span>Confidence: {pct(status?.confidence)}</span></div>{status?.evidence&&<details><summary>Mapping evidence</summary><p>{status.evidence}</p></details>}</div>})}</div>

    <div className="candidateHeader"><div><small>OCR CANDIDATE INTELLIGENCE</small><h3>Detected values not hidden by field mapping</h3></div><span className="candidateCount">{result.candidate_count??0} candidate(s)</span></div><p className="candidateNote">A value can be valid OCR but remain unmapped when DigiX cannot safely decide whether it is the due date, bill date, previous amount, payable amount, etc.</p>
    {groups.length===0?<p className="emptyCandidates">No additional structured OCR candidates were detected.</p>:<div className="candidateGroups">{groups.map(group=><section className="candidateGroup" key={group.key}><h4>{label(group.key)} <span>{group.items.length}</span></h4><div className="candidateList">{group.items.map((item,i)=><div className="candidateItem" key={`${group.key}-${i}`}><div className="candidateValue"><b>{item.currency?`${item.currency} `:""}{display(item.value)}</b><span>{pct(item.confidence)}</span></div>{item.normalized&&item.normalized!==String(item.value)&&<p><strong>Normalized:</strong> {item.normalized}</p>}<p><strong>Source:</strong> {item.source}{item.line_no?` · OCR line ${item.line_no}`:""}</p><details><summary>OCR evidence</summary><p>{item.evidence}</p></details></div>)}</div></section>)}</div>}

    <h3>Recommended actions</h3>{result.actions.map((x,i)=><p className="action" key={i}><b>{i+1}</b> {x}</p>)}
    <details className="rawPanel"><summary>Raw OCR text — everything read from the document</summary><p className="warning">This may contain personal or sensitive information.</p><pre>{result.raw_text||"No raw OCR text available."}</pre></details>
    <details className="rawPanel"><summary>Full API result — JSON</summary><pre>{JSON.stringify(result,null,2)}</pre></details>
   </section>

   <section className="card"><small>ASK YOUR DOCUMENT</small><h2>Ask mapped fields or detected candidates</h2><p className="muted">Try: “Show all detected dates”, “Show all amounts”, “Show detected IDs”, or “What name was detected?”</p><div className="askrow"><input value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>e.key==="Enter"&&ask()} placeholder="Ask a specific question…"/><button disabled={!question.trim()||asking} onClick={ask}>{asking?"Finding…":"Ask"}</button></div>{answer&&<div className={answer.grounded?"answer":"answer notFound"}><b>{answer.answer}</b><p>{answer.grounded?`Grounded in document data · ${pct(answer.confidence)} confidence`:"No reliable mapped answer was found."}</p>{answer.evidence.length>0&&<details><summary>Evidence</summary>{answer.evidence.map((x,i)=><p key={i}>{x}</p>)}</details>}</div>}</section>
  </>}
 </main>
}

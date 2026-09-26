import { useMemo, useState } from "react";

type FieldStatus = {
  status: string;
  confidence: number;
  source: string;
  evidence?: string | null;
};

type Analysis = {
  document_type: string;
  filename: string;
  summary: string;
  confidence: number;
  ocr_quality: number;
  extraction_completeness: number;
  extracted_fields: Record<string, unknown>;
  field_status: Record<string, FieldStatus>;
  actions: string[];
  document_id?: string;
};

type Answer = {
  answer: string;
  confidence: number;
  grounded: boolean;
  evidence: string[];
};

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const FIELD_ORDER = [
  "provider", "consumer_number", "reference_number", "meter_number", "tariff",
  "bill_month", "billing_period", "document_date", "due_date", "units_consumed",
  "previous_reading", "current_reading", "current_charges", "taxes_surcharges",
  "arrears", "amount_before_due", "amount_after_due", "currency"
];

const label = (key: string) => key.replaceAll("_", " ");
const pct = (n: number) => `${Math.round(n * 100)}%`;

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [asking, setAsking] = useState(false);

  const visibleFields = useMemo(() => {
    if (!result) return [];
    return FIELD_ORDER.map(key => ({
      key,
      value: result.extracted_fields[key],
      status: result.field_status[key]
    }));
  }, [result]);

  async function analyze() {
    if (!file) return;
    setBusy(true);
    setError("");
    setResult(null);
    setAnswer(null);

    const body = new FormData();
    body.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/api/v1/documents/analyze`, {
        method: "POST",
        body
      });
      if (!response.ok) throw new Error(await response.text());
      setResult(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to connect to backend.");
    } finally {
      setBusy(false);
    }
  }

  async function ask() {
    if (!result?.document_id || !question.trim()) return;
    setAsking(true);
    setError("");
    setAnswer(null);

    try {
      const response = await fetch(`${API_BASE}/api/v1/documents/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_id: result.document_id,
          question
        })
      });
      if (!response.ok) throw new Error(await response.text());
      setAnswer(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Question failed.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <main>
      <header>
        <b>DigiX <i>DocAI</i></b>
        <span>v0.5 Document Intelligence</span>
      </header>

      <section className="hero">
        <small>DOCUMENT INTELLIGENCE</small>
        <h1>Upload anything.<br />Understand it. <em>Ask it. Act on it.</em></h1>
        <p>Layout-aware extraction, field validation and grounded document Q&amp;A.</p>
      </section>

      <section className="card upload">
        <h2>Analyze a document</h2>
        <p>PDF, JPG or PNG · maximum 10 MB</p>
        <label className="filePicker">
          <input
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={e => setFile(e.target.files?.[0] || null)}
          />
          {file ? file.name : "Choose document"}
        </label>
        <button disabled={!file || busy} onClick={analyze}>
          {busy ? "Reading and understanding document…" : "Analyze document"}
        </button>
        {error && <p className="error">{error}</p>}
      </section>

      {result && <>
        <section className="card">
          <div className="top">
            <div>
              <small>ANALYSIS</small>
              <h2>{label(result.document_type)}</h2>
            </div>
            <div className="metrics">
              <div><small>TYPE CONFIDENCE</small><b>{pct(result.confidence)}</b></div>
              <div><small>OCR QUALITY</small><b>{pct(result.ocr_quality)}</b></div>
              <div><small>EXTRACTION</small><b>{pct(result.extraction_completeness)}</b></div>
            </div>
          </div>

          <p>{result.summary}</p>

          <h3>Document information</h3>
          <div className="fieldGrid">
            {visibleFields.map(({key, value, status}) => {
              const extracted =
                status?.status === "extracted" &&
                value !== undefined && value !== null && value !== "";

              return <div className={`field ${extracted ? "fieldGood" : "fieldMissing"}`} key={key}>
                <div className="fieldHead">
                  <small>{label(key)}</small>
                  {extracted
                    ? <span className="good">✓ {pct(status.confidence)}</span>
                    : <span className="missing">Not reliably read</span>}
                </div>
                <b>{extracted ? String(value) : "—"}</b>
                {extracted && status.evidence && <details>
                  <summary>Evidence</summary>
                  <p>{status.evidence}</p>
                </details>}
              </div>;
            })}
          </div>

          <h3>Recommended actions</h3>
          {result.actions.map((x, i) =>
            <p className="action" key={i}><b>{i + 1}</b> {x}</p>
          )}
        </section>

        <section className="card">
          <small>ASK YOUR DOCUMENT</small>
          <h2>What would you like to know?</h2>
          <p className="muted">
            Ask “What is the due date?”, “What is the consumer number?” or
            “What is the amount before the due date?”
          </p>

          <div className="askrow">
            <input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === "Enter" && ask()}
              placeholder="Ask a specific question…"
            />
            <button disabled={!question.trim() || asking} onClick={ask}>
              {asking ? "Finding…" : "Ask"}
            </button>
          </div>

          {answer && <div className={answer.grounded ? "answer" : "answer notFound"}>
            <b>{answer.answer}</b>
            <p>
              {answer.grounded
                ? `Grounded answer · ${pct(answer.confidence)} confidence`
                : "No reliable answer was extracted."}
            </p>
            {answer.evidence.length > 0 && <details>
              <summary>Evidence</summary>
              {answer.evidence.map((x, i) => <p key={i}>{x}</p>)}
            </details>}
          </div>}
        </section>
      </>}
    </main>
  );
}

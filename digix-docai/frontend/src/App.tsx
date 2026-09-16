import { useState } from 'react'
import { analyzeDocument } from './api'
import type { DocumentAnalysis } from './types'

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<DocumentAnalysis | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function runAnalysis() {
    if (!file) return
    setBusy(true); setError(''); setResult(null)
    try { setResult(await analyzeDocument(file)) }
    catch (e) { setError(e instanceof Error ? e.message : 'Something went wrong') }
    finally { setBusy(false) }
  }

  return (
    <main>
      <header>
        <div className="brand">DigiX <span>DocAI</span></div>
        <div className="badge">MVP 0.1</div>
      </header>

      <section className="hero">
        <p className="eyebrow">DOCUMENT INTELLIGENCE</p>
        <h1>Upload anything.<br/>Understand it. <span>Act on it.</span></h1>
        <p className="sub">Turn bills, invoices, receipts, notices and PDFs into useful information and clear next actions.</p>
      </section>

      <section className="card upload">
        <div className="icon">↥</div>
        <h2>Analyze a document</h2>
        <p>PDF, JPG or PNG · maximum 10 MB</p>
        <label className="picker">
          <input type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
            onChange={e => setFile(e.target.files?.[0] || null)} />
          {file ? file.name : 'Choose document'}
        </label>
        <button disabled={!file || busy} onClick={runAnalysis}>
          {busy ? 'Understanding document…' : 'Analyze document'}
        </button>
        {error && <div className="error">{error}</div>}
      </section>

      {result && <section className="card result">
        <div className="resultTop">
          <div><p className="eyebrow">ANALYSIS</p><h2>{result.document_type.replaceAll('_',' ')}</h2></div>
          <div className="confidence">{Math.round(result.confidence * 100)}% confidence</div>
        </div>
        <p className="summary">{result.summary}</p>

        <h3>Key information</h3>
        <div className="grid">
          {Object.entries(result.extracted_fields).map(([k,v]) =>
            v !== null && v !== '' ? <div className="field" key={k}><small>{k.replaceAll('_',' ')}</small><strong>{String(v)}</strong></div> : null
          )}
        </div>

        <h3>Recommended actions</h3>
        <div className="actions">
          {result.actions.map((a,i) => <div key={a}><b>{i+1}</b><span>{a}</span></div>)}
        </div>
      </section>}

      <footer>Built for DigiXDreams · Privacy-first MVP</footer>
    </main>
  )
}

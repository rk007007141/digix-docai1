import type { DocumentAnalysis } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function analyzeDocument(file: File): Promise<DocumentAnalysis> {
  const form = new FormData()
  form.append('file', file)

  const response = await fetch(`${API_BASE}/api/v1/documents/analyze`, {
    method: 'POST',
    body: form,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || 'Document analysis failed')
  }
  return response.json()
}

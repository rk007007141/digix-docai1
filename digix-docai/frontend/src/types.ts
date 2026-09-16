export type DocumentAnalysis = {
  document_type: string
  filename: string
  provider?: string | null
  document_date?: string | null
  due_date?: string | null
  amount?: number | null
  currency?: string | null
  summary: string
  actions: string[]
  confidence: number
  extracted_fields: Record<string, string | number | null>
}

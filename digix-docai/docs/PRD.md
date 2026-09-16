# DigiX DocAI — MVP PRD

## Problem
People receive bills, invoices, receipts, notices and PDFs but often need to manually find important amounts, dates and required actions.

## Promise
Upload anything. Understand it. Act on it.

## V0.1
Supported input: PDF, JPG, PNG.
Core categories: bill, invoice, receipt, notice, generic document.
Core output: classification, key fields, concise explanation, confidence and recommended actions.

## Acceptance criteria
1. User can select a supported file.
2. Unsupported files and oversized uploads are rejected.
3. UI shows a processing state.
4. Backend returns structured JSON.
5. UI renders classification, summary, fields, confidence and actions.
6. No customer file or secret is committed to source control.
7. App runs locally without a paid AI account.

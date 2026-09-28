# ADR 0004: PII and Data Governance

## Status
Accepted

## Context
Citizen complaints contain personally identifiable information (PII): names, addresses, phone numbers, and descriptions of problems at specific locations. When using a hosted LLM (Groq), this data leaves our infrastructure. On the free tier, the provider may use inputs to improve its models.

### What leaves the machine
When `TRIAGE_PROVIDER=llm`:
- **Complaint text** (may contain names, phone numbers)
- **Location** (street addresses)
- These are sent to Groq's API endpoint over HTTPS

When `TRIAGE_PROVIDER=ollama`:
- **Nothing leaves the machine** — inference runs locally

When `TRIAGE_PROVIDER=rules`:
- **Nothing leaves the machine** — keyword matching only

## Decision
We adopt a **tiered approach**:

### 1. Default to local processing
The default `TRIAGE_PROVIDER` is `rules` — no data ever leaves the machine unless explicitly configured.

### 2. Send only complaint body to LLM
When using the hosted LLM:
- We send **only** the complaint text and location
- We do **not** send `reporter_contact` to the LLM
- The system prompt treats complaint text as untrusted data

### 3. Document the exposure
This ADR serves as the explicit documentation that:
- Groq free tier may use inputs for model improvement
- Complaint text sent to Groq contains citizen descriptions of municipal issues
- Location data is sent for classification accuracy
- Contact information is **never** sent to external services

### 4. Provide a zero-PII path
`TRIAGE_PROVIDER=ollama` runs a local model — no PII leaves the machine. This is the recommended path for deployments handling sensitive data.

## Alternatives Considered
- **Redact PII before sending**: Would require NER (Named Entity Recognition) which adds complexity and may reduce classification accuracy. The complaint text IS the data we need to classify.
- **Send only anonymized summaries**: Defeats the purpose of AI triage.
- **Don't use hosted LLM at all**: Viable via Ollama, but hosted models are faster and more accurate.

## Consequences
- Organizations must choose their provider based on their data governance requirements
- The `triaged_by` column records whether data went to an external service
- Switching between hosted and local is a single environment variable change
- This ADR must be reviewed when changing LLM providers

## References
- `backend/app/providers/triage/llm.py` — Only text and location are sent (lines with `USER_PROMPT_TEMPLATE`)
- `backend/app/config.py` — `TRIAGE_PROVIDER` setting
- `backend/app/providers/triage/ollama.py` — Zero-PII local path

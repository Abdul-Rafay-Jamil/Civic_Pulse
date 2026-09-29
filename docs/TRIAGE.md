# Triage System Documentation


### Fallback Chain
When the primary LLM provider (Groq/Ollama) fails due to timeout (10s hard cap),
rate limiting (429), or server error (5xx), the system retries once with jitter.
If the retry also fails, it falls back to RuleBasedTriage and records
`triaged_by = "rules:fallback"`. A WARNING log is emitted with the complaint ID,
provider name, and error class. The citizen never sees a 500.


## Overview

CivicPulse's triage system classifies citizen complaints into:
- **Category**: water, electricity, sanitation, roads, streetlights, other
- **Priority**: high, normal, low
- **Summary**: One-line description (≤ 140 chars)
- **Confidence**: 0.0–1.0 score

## Provider Architecture

```
┌─────────────────────────────────────────────┐
│              TriageProvider Protocol         │
│  name: str                                   │
│  triage(text, location) → TriageResult       │
└─────────────────────────────────────────────┘
         │              │              │              │
    ┌────┴────┐   ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
    │ LLMTriage│   │OllamaTri│   │RuleBase │   │Simulated│
    │ (Groq)  │   │ (Local) │   │ (Fallbk)│   │  (CI)   │
    └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

## Resilience Chain

1. **Try primary provider** (configured via `TRIAGE_PROVIDER`)
2. **Timeout**: 10-second hard cap
3. **Retry**: Once, with jitter (0.5–1.5s), only on retryable errors (timeout, 429, 5xx)
4. **Fallback**: `RuleBasedTriage` — always succeeds
5. **Record**: `triaged_by` column shows exactly what happened

## Content-Hash Caching

Duplicate complaints (same text + location) hit a Redis cache (24h TTL), saving LLM calls. This is keyed by SHA-256 of `text|location`.

## Prompt Injection Protection

- Complaint text is delimited with `<complaint>` tags
- System prompt explicitly states the text is untrusted user input
- Output is constrained to valid enum values
- Pydantic validation rejects anything outside the schema
- Test: `test_prompt_injection_rejected` in `tests/test_providers.py`

## Measured Metrics

- `triaged_by` — which provider produced the result
- `triage_latency_ms` — time taken for triage
- Cache hit rate — available via `/api/meta/providers`
- Fallback count — logged as WARNING, surfaced in provider info

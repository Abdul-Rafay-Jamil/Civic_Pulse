# ADR 0001: Provider Interface for AI Triage

## Status
Accepted

## Context
The system needs to classify citizen complaints into categories, priorities, and summaries. Today the reader is a keyword rule, tomorrow it might be a language model, next year a fine-tuned classifier. The system must not care which provider is active, and must not fail when the provider is rate-limited, slow, or wrong.

## Decision
We use a **Protocol-based interface** (`TriageProvider`) that all providers implement. The provider is selected at startup via the `TRIAGE_PROVIDER` environment variable, instantiated by a factory function.

### Interface
```python
class TriageProvider(Protocol):
    name: str
    async def triage(self, text: str, location: str) -> TriageResult: ...
```

### Implementations
1. **LLMTriage** (`llm`) — Groq API via OpenAI SDK. Production path.
2. **OllamaTriage** (`ollama`) — Local container, no network egress.
3. **RuleBasedTriage** (`rules`) — Deterministic keyword fallback. Always available.
4. **SimulatedTriage** (`simulated`) — Deterministic fake for CI. Seeded, no network.

### Resilience Chain
1. Structured output requested (JSON mode) + Pydantic validation
2. 10-second hard timeout on every call
3. Single retry with jitter on retryable errors (timeout, 429, 5xx)
4. Fallback to `RuleBasedTriage` with `triaged_by = "rules:fallback"`

## Alternatives Considered
- **Abstract Base Class**: More rigid, requires inheritance. Protocol is more Pythonic and allows duck typing.
- **Strategy pattern with registration**: Over-engineering for 4 providers.
- **Direct LLM coupling**: Would make testing non-deterministic and create a single point of failure.

## Consequences
- Any new provider just needs to implement `triage()` and return a `TriageResult`.
- CI is always deterministic via `SimulatedTriage`.
- Users never see a 500 because a third-party API was rate-limited.
- The `triaged_by` column records exactly which provider produced each result.

## References
- `backend/app/providers/triage/base.py` — Protocol definition
- `backend/app/providers/triage/factory.py` — Factory function
- `backend/app/services/complaint_service.py` — Resilience orchestration

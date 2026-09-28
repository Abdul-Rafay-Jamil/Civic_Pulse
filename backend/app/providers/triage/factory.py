"""Provider factory — selects the triage provider by TRIAGE_PROVIDER env var."""

from app.config import settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.llm import LLMTriage
from app.providers.triage.ollama import OllamaTriage
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


def create_triage_provider(provider_name: str | None = None) -> TriageProvider:
    """Instantiate the triage provider based on configuration.

    Args:
        provider_name: Override for the provider. Defaults to TRIAGE_PROVIDER env var.

    Returns:
        A TriageProvider implementation.
    """
    name = (provider_name or settings.triage_provider).lower().strip()

    match name:
        case "llm" | "groq":
            return LLMTriage()  # type: ignore[return-value]
        case "ollama":
            return OllamaTriage()  # type: ignore[return-value]
        case "rules":
            return RuleBasedTriage()  # type: ignore[return-value]
        case "simulated":
            return SimulatedTriage()  # type: ignore[return-value]
        case _:
            raise ValueError(
                f"Unknown TRIAGE_PROVIDER: {name!r}. "
                f"Valid options: llm, ollama, rules, simulated"
            )

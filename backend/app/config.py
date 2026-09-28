"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://civicpulse:civicpulse@database:5432/civicpulse",
        alias="DATABASE_URL",
    )

    # Redis
    redis_url: str = Field(default="redis://cache:6379/0", alias="REDIS_URL")

    # AI Triage
    triage_provider: str = Field(default="rules", alias="TRIAGE_PROVIDER")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    llm_model: str = Field(default="llama-3.1-8b-instant", alias="LLM_MODEL")
    ollama_base_url: str = Field(default="http://ollama:11434", alias="OLLAMA_BASE_URL")

    # Rate Limiting
    rate_limit_requests: int = Field(default=30, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    # Application
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}


settings = Settings()

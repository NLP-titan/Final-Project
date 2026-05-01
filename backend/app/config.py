import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_JWT_SECRET = "please-change-me-in-production-this-is-only-for-dev"
DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "changeme123"

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment ("development" | "production"). When `production`, the app
    # refuses to start with default secrets or wildcard CORS.
    app_env: str = "development"

    # LLM
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "openai/gpt-5.4" 
    judge_model: str = "google/gemini-3.1-pro-preview"  # model used by the eval LLM judge

    # Embedding / vector store
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_persist_dir: str = str(BACKEND_ROOT / "data" / "processed" / "chroma")
    chroma_collection: str = "nhis_policies"

    # Seed data
    medicines_csv: str = str(BACKEND_ROOT / "data" / "raw" / "medicines.csv")
    facilities_csv: str = str(BACKEND_ROOT / "data" / "raw" / "facilities.csv")
    policies_dir: str = str(BACKEND_ROOT / "data" / "raw" / "policies")
    knowledge_base_dir: str = str(BACKEND_ROOT / "data" / "raw" / "knowledge_base")

    # DB
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'data' / 'processed' / 'app.db'}"

    # Auth
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 1440

    # Initial admin (auto-created if no admin exists)
    initial_admin_email: str = DEFAULT_ADMIN_EMAIL
    initial_admin_password: str = DEFAULT_ADMIN_PASSWORD

    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_chat_per_minute: int = 20

    # Agent loop
    agent_max_tool_iterations: int = 4
    agent_max_history_turns: int = 10

    # LLM retry
    llm_retry_attempts: int = 3
    llm_retry_base_delay: float = 0.5
    llm_retry_max_delay: float = 4.0

    # Logging
    log_level: str = "INFO"

    # CORS
    cors_origins: str = "*"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_production_safe(self) -> list[str]:
        """Returns a list of misconfiguration error strings.

        In production the app will refuse to start if this list is non-empty.
        In development the same list is logged as warnings.
        """
        errors: list[str] = []
        if self.jwt_secret == DEFAULT_JWT_SECRET:
            errors.append("JWT_SECRET is still the default — set a long random secret.")
        if self.initial_admin_email == DEFAULT_ADMIN_EMAIL:
            errors.append("INITIAL_ADMIN_EMAIL is still the default — set a real admin email.")
        if self.initial_admin_password == DEFAULT_ADMIN_PASSWORD:
            errors.append("INITIAL_ADMIN_PASSWORD is still the default — set a strong password.")
        if self.cors_origins.strip() == "*":
            errors.append("CORS_ORIGINS is wildcard '*' — set a comma-separated list of allowed origins.")
        if self.database_url.startswith("sqlite:"):
            errors.append("DATABASE_URL is SQLite — switch to a managed Postgres for production.")
        return errors


settings = Settings()


def assert_production_safe() -> None:
    """Call once during startup. Fails loudly in production, warns in dev."""
    issues = settings.validate_production_safe()
    if not issues:
        return
    if settings.is_production:
        joined = "\n  - ".join(issues)
        raise RuntimeError(
            "Refusing to start: APP_ENV=production but the following are misconfigured:\n  - "
            + joined
        )
    for issue in issues:
        log.warning("Config (dev): %s", issue)

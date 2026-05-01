from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "~google/gemini-pro-latest"
    judge_model: str = "openai/gpt-5.4"  # model used by the eval LLM judge

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
    jwt_secret: str = "please-change-me-in-production-this-is-only-for-dev"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 1440

    # Initial admin (auto-created if no admin exists)
    initial_admin_email: str = "admin@example.com"
    initial_admin_password: str = "changeme123"

    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_chat_per_minute: int = 20

    # Logging
    log_level: str = "INFO"

    # CORS
    cors_origins: str = "*"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

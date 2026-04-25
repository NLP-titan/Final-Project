from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    chroma_persist_dir: str = str(BACKEND_ROOT / "data" / "processed" / "chroma")
    chroma_collection: str = "nhis_policies"

    medicines_csv: str = str(BACKEND_ROOT / "data" / "raw" / "medicines.csv")
    facilities_csv: str = str(BACKEND_ROOT / "data" / "raw" / "facilities.csv")
    policies_dir: str = str(BACKEND_ROOT / "data" / "raw" / "policies")

    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()

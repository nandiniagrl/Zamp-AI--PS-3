"""Central settings. Secrets are SecretStr so they never print in logs/reprs."""
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    # Groq
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_fast_model: str = "openai/gpt-oss-20b"
    groq_timeout_s: float = 30.0
    groq_max_retries: int = 2
    # Tavily
    tavily_api_key: SecretStr | None = None
    tavily_timeout_s: float = 20.0
    tavily_max_results: int = 5
    # Cache
    cache_enabled: bool = True
    cache_dir: Path = BACKEND_DIR / ".cache"
    cache_ttl_hours: int = 24
    # Persistence (Phase 10+)
    storage_backend: str = "sqlite"
    checkpoint_backend: str = "sqlite"
    data_dir: Path = BACKEND_DIR / ".data"
    database_url: SecretStr | None = None
    gcp_project: str | None = None
    # API
    cors_origins: str = "http://localhost:3000"

    def key_status(self) -> dict[str, str]:
        """Report presence of credentials WITHOUT revealing them."""

        def state(v: SecretStr | None) -> str:
            return "present" if v is not None and v.get_secret_value().strip() else "missing"

        return {"GROQ_API_KEY": state(self.groq_api_key), "TAVILY_API_KEY": state(self.tavily_api_key)}


@lru_cache
def get_settings() -> Settings:
    return Settings()

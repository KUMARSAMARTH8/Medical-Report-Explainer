"""
config.py

Central, typed configuration for the whole backend, loaded from environment
variables / a `.env` file. Nothing else in the codebase should call
`os.getenv` directly — import `settings` from here instead, so every
tunable value lives in one place and is documented once.

Copy `.env.example` to `.env` and edit values there; `.env` is gitignored
so secrets/local overrides never get committed.
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "AI Medical Report Explainer"
    app_version: str = "2.0.0"
    environment: str = "development"          # development | staging | production
    log_level: str = "INFO"                    # DEBUG | INFO | WARNING | ERROR

    # --- Server ---
    host: str = "127.0.0.1"
    port: int = 8000

    # --- CORS ---
    # Comma-separated list of allowed origins, e.g. "http://localhost:5500,https://myapp.com"
    # "*" allows any origin (fine for local dev, NOT recommended for production).
    cors_origins: str = "*"

    # --- Uploads ---
    max_upload_size_mb: int = 10
    allowed_extensions: str = ".pdf,.png,.jpg,.jpeg,.bmp,.tiff"
    reports_dir: str = "reports"
    delete_files_after_processing: bool = True   # don't retain raw uploads once parsed

    # --- Database ---
    db_path: str = "reports.db"

    # --- Optional NLP upgrades (see nlp/chatbot.py) ---
    enable_semantic_chatbot: bool = False   # requires sentence-transformers installed

    # --- Rate limiting (simple, in-memory) ---
    rate_limit_per_minute: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_extension_set(self) -> set[str]:
        return {ext.strip().lower() for ext in self.allowed_extensions.split(",") if ext.strip()}


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is only parsed once per process."""
    return Settings()


settings = get_settings()

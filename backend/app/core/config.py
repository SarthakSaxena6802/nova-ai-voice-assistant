"""Application configuration loaded from environment variables / .env files.

"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent

APP_VERSION = "1.0.0"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_DIR / ".env"), str(BACKEND_DIR / ".env")),
        env_prefix="NOVA_",
        extra="ignore",
    )

    # --- General -----------------------------------------------------------
    app_name: str = "Nova"
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Storage -----------------------------------------------------------
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'nova.db').as_posix()}"

    # --- Machine learning ----------------------------------------------------
    model_path: Path = BACKEND_DIR / "artifacts" / "intent_model.joblib"
    model_report_path: Path = BACKEND_DIR / "artifacts" / "training_report.json"
    dataset_path: Path = BACKEND_DIR / "datasets" / "intents.json"
    unseen_dataset_path: Path = BACKEND_DIR / "datasets" / "intents_unseen.json"
    knowledge_base_path: Path = BACKEND_DIR / "datasets" / "knowledge_base.json"
    auto_train_if_missing: bool = True

    # --- Runtime behaviour ------------------------------------------------------
    # Open allow-listed websites with the OS default browser (the backend runs locally).
    open_browser_on_server: bool = True
    scheduler_interval_seconds: float = 1.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()

import logging
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "ArteFact Retell API")
    app_env: str = os.getenv("APP_ENV", "development")
    database_path: str = os.getenv("DATABASE_PATH", "artifact_retell.db")
    cors_origins_raw: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    retell_api_key: str = os.getenv("RETELL_API_KEY", "")
    retell_base_url: str = os.getenv("RETELL_BASE_URL", "https://api.retellai.com")
    retell_voice_id: str = os.getenv("RETELL_VOICE_ID", "retell-Cimo")
    retell_from_number: str = os.getenv("RETELL_FROM_NUMBER", "")
    retell_webhook_url: str = os.getenv("RETELL_WEBHOOK_URL", "")
    retell_model: str = os.getenv("RETELL_MODEL", "gpt-4.1-mini")
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

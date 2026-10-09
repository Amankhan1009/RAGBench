"""Application settings and database URL normalization for Neon PostgreSQL."""
import re

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "RAGBench"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"
    ENCRYPTION_KEY: str = "dGhpcy1pcy1hLXRlc3QtZW5jcnlwdGlvbi1rZXktMTIzNDU="
    FERNET_KEY: str | None = None
    SECRET_KEY: str = "default-production-secret-key-change-me"
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""

    @computed_field
    @property
    def effective_encryption_key(self) -> str:
        """Resolve either FERNET_KEY or ENCRYPTION_KEY seamlessly."""
        return self.FERNET_KEY or self.ENCRYPTION_KEY

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @computed_field
    @property
    def async_database_url(self) -> str:
        """Normalize Neon PostgreSQL URLs for asyncpg driver compatibility."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if "sslmode=" in url:
            url = url.replace("sslmode=", "ssl=")
        url = re.sub(r"[&?]channel_binding=[^&]*", "", url)
        return url


settings = Settings()

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):

    DEBUG: bool = False

    # Database settings
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    VERIFY_TOKEN_EXPIRE_HOURS: int

    # Security settings
    CSRF_SECRET_KEY: str

    # Email настройки
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str
    EMAIL_FROM_NAME: str
    SMTP_USE_TLS: bool
    SMTP_USE_SSL: bool

    # Frontend URLs
    FRONTEND_URL: str
    VERIFY_EMAIL_URL: str

    # Backend URLs
    BACKEND_URL: str

    @property
    def DATABASE_URL(self) -> str:
        """Генерирует URL для подключения к PostgreSQL"""
        return (
            f"postgresql+psycopg2://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    class Config:
        case_sensitive = False
        env_file = ".env"
        extra = "ignore"


settings = Settings()

DATABASE_URL = settings.DATABASE_URL

__all__ = ["settings", "DATABASE_URL"]
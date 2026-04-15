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

    DATABASE_URL: str

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    VERIFY_TOKEN_EXPIRE_HOURS: int
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int
    SESSION_TIMEOUT_MINUTES: int
    MAX_FAILED_LOGIN_ATTEMPTS: int
    ACCOUNT_LOCKOUT_MINUTES: int

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
    REDIS_URL: str

    # Backend URLs
    BACKEND_URL: str

    @property
    def db_url(self) -> str:
        """Возвращает URL для подключения к PostgreSQL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
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
DATABASE_URL = settings.db_url

__all__ = ["settings", "DATABASE_URL"]
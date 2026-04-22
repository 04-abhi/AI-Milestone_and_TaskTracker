from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "AI Task Tracker"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-min-32-chars-change-this!!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:root@localhost:5432/ait_v3"
    DATABASE_URL_SYNC: str = "postgresql://postgres:root@localhost:5432/ait_v3"

    # Admin seed
    FIRST_ADMIN_EMAIL: str = "admin@ait.com"
    FIRST_ADMIN_PASSWORD: str = "Admin@1234"
    FIRST_ADMIN_USERNAME: str = "admin"

    # Web Push VAPID
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CLAIMS_EMAIL: str = "admin@ait.com"

    # Groq AI (https://console.groq.com)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_API_BASE: str = "https://api.groq.com/openai/v1"

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

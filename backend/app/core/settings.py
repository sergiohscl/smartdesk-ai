from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Configurações da Inteligência Artificial
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = 'gpt-6-luna'
    AI_TIMEOUT_SECONDS: int = 15
    AI_MAX_OUTPUT_TOKENS: int = 300
    AI_MAX_DESCRIPTION_CHARS: int = 4000
    AI_DAILY_USER_LIMIT: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]

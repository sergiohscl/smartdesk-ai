from functools import lru_cache
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    Field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.chat_model_policy import (
    DEFAULT_CHAT_MODEL,
    validate_local_chat_model,
)
from app.core.ollama_url_policy import validate_local_ollama_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        secrets_dir='/run/secrets',
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

    # SmartDesk Assistant
    CHAT_ENABLED: bool = True
    CHAT_PROVIDER: Literal['ollama'] = 'ollama'
    CHAT_MODEL: str = Field(
        default=DEFAULT_CHAT_MODEL,
        min_length=1,
        max_length=100,
    )

    # Ollama
    OLLAMA_BASE_URL: AnyHttpUrl = Field(
        default='http://ollama:11434',
    )
    OLLAMA_TEMPERATURE: float = Field(
        default=0.1,
        ge=0,
        le=2,
        allow_inf_nan=False,
    )
    OLLAMA_NUM_CTX: int = Field(
        default=4096,
        ge=512,
        le=32768,
    )
    OLLAMA_NUM_PREDICT: int = Field(
        default=768,
        ge=1,
        le=8192,
    )
    OLLAMA_SEED: int = Field(
        default=42,
        ge=0,
        le=2147483647,
    )
    OLLAMA_KEEP_ALIVE: str = Field(
        default='5m',
        pattern=r'^(0|[0-9]+[smh])$',
        max_length=16,
    )

    # Limites operacionais do Assistant
    CHAT_TIMEOUT_SECONDS: int = Field(
        default=120,
        ge=1,
        le=600,
    )
    CHAT_MAX_MESSAGE_CHARS: int = Field(
        default=8000,
        ge=1,
        le=8000,
    )
    CHAT_MAX_TITLE_CHARS: int = Field(
        default=150,
        ge=1,
        le=150,
    )
    CHAT_MAX_CONTEXT_MESSAGES: int = Field(
        default=20,
        ge=1,
        le=100,
    )
    CHAT_DAILY_USER_LIMIT: int = Field(
        default=50,
        ge=1,
        le=10000,
    )
    CHAT_REQUESTS_PER_MINUTE: int = Field(
        default=5,
        ge=1,
        le=1000,
    )
    CHAT_MAX_CONCURRENT_PER_USER: int = Field(
        default=1,
        ge=1,
        le=100,
    )
    CHAT_MAX_CONCURRENT_GLOBAL: int = Field(
        default=1,
        ge=1,
        le=100,
    )
    CHAT_PROMPT_VERSION: Literal['v2'] = 'v2'
    CHAT_ALLOW_PAID_FALLBACK: bool = False

    # Segurança do endpoint de monitoramento
    METRICS_TOKEN: str | None = None

    @field_validator('CHAT_MODEL')
    @classmethod
    def validate_chat_model_policy(cls, value: str) -> str:
        return validate_local_chat_model(value)

    @field_validator('CHAT_MODEL', mode='before')
    @classmethod
    def validate_chat_model(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if not value or chr(0) in value:
                raise ValueError('Invalid chat model.')
        return value

    @field_validator('OLLAMA_BASE_URL')
    @classmethod
    def validate_ollama_base_url(
        cls,
        value: AnyHttpUrl,
    ) -> AnyHttpUrl:
        return validate_local_ollama_url(value)

    @model_validator(mode='after')
    def validate_chat_settings(self):
        if self.CHAT_ALLOW_PAID_FALLBACK:
            raise ValueError('Paid fallback is not allowed.')

        if self.OLLAMA_NUM_PREDICT >= self.OLLAMA_NUM_CTX:
            raise ValueError('Output limit must be smaller than context size.')

        if self.CHAT_MAX_CONCURRENT_PER_USER > self.CHAT_MAX_CONCURRENT_GLOBAL:
            raise ValueError(
                'User concurrency cannot exceed global concurrency.'
            )

        return self

    @property
    def chat_input_token_budget(self) -> int:
        return self.OLLAMA_NUM_CTX - self.OLLAMA_NUM_PREDICT


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]

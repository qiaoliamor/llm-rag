from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    chat_provider: str = Field(default='openai', pattern='^(openai|mock)$')
    openai_api_key: SecretStr = SecretStr('')
    openai_model: str = 'gpt-4.1-mini'
    api_timeout_seconds: float = Field(default=30, ge=1, le=120)
    session_ttl_seconds: int = Field(default=7200, ge=60)
    max_sessions: int = Field(default=200, ge=1)

from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    chat_provider: str = Field(default='gemini', pattern='^(gemini|openai|mock)$')
    gemini_api_key: SecretStr = SecretStr('')
    gemini_model: str = 'gemini-2.5-flash-lite'
    openai_api_key: SecretStr = SecretStr('')
    openai_model: str = 'gpt-4.1-mini'
    api_timeout_seconds: float = Field(default=30, ge=1, le=120)
    session_ttl_seconds: int = Field(default=7200, ge=60)
    max_sessions: int = Field(default=200, ge=1)

    @property
    def api_key_env(self):
        return 'GEMINI_API_KEY' if self.chat_provider == 'gemini' else 'OPENAI_API_KEY'

    @property
    def selected_model(self):
        if self.chat_provider == 'mock':
            return '离线演示'
        return self.gemini_model if self.chat_provider == 'gemini' else self.openai_model

    @property
    def configured(self):
        if self.chat_provider == 'mock':
            return True
        key = self.gemini_api_key if self.chat_provider == 'gemini' else self.openai_api_key
        return bool(key.get_secret_value().strip())

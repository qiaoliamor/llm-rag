from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    chat_provider: str = Field(default='gemini', pattern='^(gemini|openai|mock)$')
    gemini_api_key: SecretStr = SecretStr('')
    gemini_model: str = 'gemini-3.5-flash-lite'
    memory_database_url: SecretStr = SecretStr('sqlite:///data/memory.sqlite3')
    openai_api_key: SecretStr = SecretStr('')
    openai_model: str = 'gpt-4.1-mini'
    weather_provider: str = Field(default='openmeteo', pattern='^(openmeteo|mock)$')
    weather_understanding_mode: str = Field(default='semantic', pattern='^(semantic|legacy)$')
    weather_understanding_timeout_seconds: float = Field(default=4, ge=.1, le=10)
    emotion_understanding_mode: str = Field(default='semantic', pattern='^(semantic|legacy)$')
    emotion_understanding_timeout_seconds: float = Field(default=6, ge=.1, le=10)
    api_timeout_seconds: float = Field(default=30, ge=1, le=120)
    memory_understanding_mode: str = Field(default='semantic', pattern='^(semantic|legacy)$')
    memory_understanding_timeout_seconds: float = Field(default=4, ge=.1, le=10)
    memory_router_enabled: bool = True
    semantic_review_enabled: bool = True
    dialogue_mode: str = Field(default='companion', pattern='^(companion|audit)$')
    growth_enabled: bool = True
    memory_route_timeout_seconds: float = Field(default=4, ge=.1, le=10)
    semantic_review_timeout_seconds: float = Field(default=8, ge=.1, le=20)
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

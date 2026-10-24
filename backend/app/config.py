from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://famchop:famchop@localhost:5432/famchop"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 60 * 24 * 7
    gemini_api_key: str = ""
    gemma_model: str = "gemma-4-26b-a4b-it"
    # MINIMAL keeps Gemma 4 fast; set to empty to let the model think at its default length
    gemma_thinking_level: str = "MINIMAL"
    frontend_origin: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()

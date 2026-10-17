from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://corvid:corvid@localhost:5433/corvid_dev"
    test_database_url: str = "postgresql+psycopg://corvid:corvid@localhost:5433/corvid_test"

    anthropic_api_key: str = ""
    anthropic_extraction_model: str = "claude-haiku-4-5"

    embedding_provider: str = "fastembed"
    embedding_dim: int = 384

    scoring_config_path: str = "config/scoring.yaml"

    corvid_api_base_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()

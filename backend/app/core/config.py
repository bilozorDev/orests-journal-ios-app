from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Orest's Journal API"
    environment: str = "development"
    debug: bool = False

    # Database (Neon PostgreSQL)
    database_url: str

    # JWT Authentication (Sign in with Apple + our own tokens)
    jwt_secret_key: str  # Used to sign/verify our own JWTs
    jwt_expiration_days: int = 7

    # Storage (S3/R2) - Optional for now
    s3_endpoint_url: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    s3_bucket_name: str = "orests-journal"
    s3_public_url: Optional[str] = None

    # OpenAI - Optional for now
    openai_api_key: Optional[str] = None

    # CORS
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()

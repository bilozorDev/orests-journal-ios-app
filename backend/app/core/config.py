from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    # App
    app_name: str = "Orest's Journal API"
    environment: str = "development"
    debug: bool = False

    # Database (Neon PostgreSQL)
    database_url: str

    # Redis Cache (optional)
    redis_url: Optional[str] = None

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

    # APNs (Apple Push Notifications) - Optional
    apns_key_id: Optional[str] = None
    apns_team_id: Optional[str] = None
    apns_bundle_id: str = "com.notip.orests-journal"
    apns_key_base64: Optional[str] = None  # Base64 encoded .p8 key file
    apns_use_sandbox: bool = True  # False for production

    # CORS
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()

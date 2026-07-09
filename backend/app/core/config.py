from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings
from typing import List, Optional, Union
import secrets


class Settings(BaseSettings):
    PROJECT_NAME: str = "Urban Heat Mitigation Platform"
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 7 days = 7 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "urban-heat-platform"
    JWT_AUDIENCE: str = "urban-heat-api"
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000"]'
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "urbanheat"
    POSTGRES_PORT: str = "5432"
    SQLALCHEMY_DATABASE_URI: PostgresDsn = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode='before')
    def assemble_db_connection(cls, v: Optional[str], info) -> PostgresDsn:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=info.data["POSTGRES_USER"],
            password=info.data["POSTGRES_PASSWORD"],
            host=info.data["POSTGRES_SERVER"],
            port=int(info.data["POSTGRES_PORT"]),
            path=f"/{info.data['POSTGRES_DB'] or ''}",
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: str = None

    @field_validator("REDIS_URL", mode='before')
    def assemble_redis_connection(cls, v: Optional[str], info) -> [str]:
        if isinstance(v, str):
            return v
        password = f":{info.data['REDIS_PASSWORD']}@" if info.data["REDIS_PASSWORD"] else ""
        return f"redis://{password}{info.data['REDIS_HOST']}:{info.data['REDIS_PORT']}/{info.data['REDIS_DB']}"

    # API
    API_V1_STR: str = "/api/v1"

    # Frontend URL for password reset, etc.
    FRONTEND_HOST: str = "http://localhost:5173"

    # Email settings (for notifications)
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = ""
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@urbanheat.isro.gov.in"
    EMAILS_FROM_NAME: str = "Urban Heat Mitigation Platform"

    # File upload settings
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100 MB

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Model storage
    MODEL_DIR: str = "/app/models"

    # Satellite acquisition
    SATELLITE_STORAGE_DIR: str = "/app/data/satellite"
    SATELLITE_CACHE_SIZE: int = 500
    SATELLITE_CACHE_TTL: int = 3600
    SATELLITE_MAX_CONCURRENT_DOWNLOADS: int = 4

    # Observability
    ENVIRONMENT: str = "development"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "urbanheat-backend"
    SENTRY_DSN: str = ""

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


settings = Settings()
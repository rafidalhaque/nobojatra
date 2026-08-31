from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    log_level: str = "info"
    cors_origins: str = "http://localhost:5173"

    jwt_secret: str = "change-me"
    jwt_expiry_seconds: int = 3600
    cookie_secure: bool = True
    cookie_domain: str = ""

    database_url: str = "postgresql+asyncpg://nobojatra_app:app-pw@localhost:5432/nobojatra"
    database_url_owner: str = (
        "postgresql+asyncpg://nobojatra_owner:owner-pw@localhost:5432/nobojatra"
    )
    # Runtime role name — RLS policies and GRANTs target it. Must match DATABASE_URL's user.
    app_db_user: str = "nobojatra_app"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "nobojatra-media"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_sse: str = "AES256"

    ntfy_url: str = "http://localhost:8080"
    ntfy_topic_prefix: str = "portal-dev"
    ntfy_token: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

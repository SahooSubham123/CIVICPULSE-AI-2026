from functools import lru_cache
import re
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CIVICPULSE AI API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./civicpulse.db"
    migration_database_url: SecretStr | None = None
    auto_create_schema: bool = True
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)
    database_ssl_mode: str = Field(default="require", pattern="^(disable|require|verify-ca|verify-full)$")
    database_rls_role: str = Field(default="civicpulse_app", pattern="^[a-z][a-z0-9_]{0,62}$")
    jwt_secret_key: SecretStr = SecretStr("development-only-change-this-secret")
    jwt_algorithm: str = Field(default="HS256", pattern="^(HS256|HS384|HS512)$")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    cors_origins: list[str] = ["http://localhost:5173"]
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    openai_transcription_model: str = "gpt-4o-mini-transcribe"
    ai_provider: str = Field(default="openai", pattern="^(openai|gemini)$")
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: SecretStr | None = None
    max_media_size_bytes: int = Field(default=10_485_760, ge=1_024, le=52_428_800)
    policy_pdf_max_size_bytes: int = Field(default=20_971_520, ge=1_024, le=104_857_600)
    policy_pdf_max_pages: int = Field(default=2_000, ge=1, le=20_000)
    policy_pdf_max_extracted_chars: int = Field(default=5_000_000, ge=10_000, le=50_000_000)
    policy_chunk_size_chars: int = Field(default=1_600, ge=200, le=8_000)
    policy_chunk_overlap_chars: int = Field(default=200, ge=0, le=2_000)
    policy_min_similarity: float = Field(default=0.35, ge=0, le=1)
    policy_retrieval_limit: int = Field(default=5, ge=1, le=20)
    government_service_portals: dict[str, str] = Field(default_factory=dict)
    trusted_fact_source_domains: list[str] = Field(default_factory=list)

    @field_validator("trusted_fact_source_domains")
    @classmethod
    def validate_trusted_fact_source_domains(cls, domains: list[str]) -> list[str]:
        normalized = [domain.lower().strip().rstrip(".") for domain in domains]
        if any(
            not re.fullmatch(
                r"(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
                r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*",
                domain,
            )
            or domain == "localhost"
            or domain.endswith(".local")
            or re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", domain)
            for domain in normalized
        ):
            raise ValueError("Trusted fact-source entries must be plain hostnames.")
        return normalized

    @field_validator("government_service_portals")
    @classmethod
    def validate_government_service_portals(cls, portals: dict[str, str]) -> dict[str, str]:
        for portal_id, portal_url in portals.items():
            parsed = urlsplit(portal_url)
            if (
                not re.fullmatch(r"[a-z][a-z0-9_-]{1,39}", portal_id)
                or parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.port not in (None, 443)
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "Government service portals must use an ID and a credential-free HTTPS URL on the default port."
                )
        return portals

    @model_validator(mode="after")
    def validate_policy_chunking(self) -> "Settings":
        if self.policy_chunk_overlap_chars >= self.policy_chunk_size_chars:
            raise ValueError("POLICY_CHUNK_OVERLAP_CHARS must be smaller than POLICY_CHUNK_SIZE_CHARS.")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment.lower() == "production":
            if len(self.jwt_secret_key.get_secret_value()) < 32:
                raise ValueError("JWT_SECRET_KEY must contain at least 32 characters in production.")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Use PostgreSQL rather than SQLite in production.")
            if self.auto_create_schema:
                raise ValueError("Set AUTO_CREATE_SCHEMA=false in production and apply migrations before startup.")
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production DATABASE_URL must use the psycopg PostgreSQL driver.")
            if self.database_ssl_mode == "disable":
                raise ValueError("DATABASE_SSL_MODE must require TLS in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

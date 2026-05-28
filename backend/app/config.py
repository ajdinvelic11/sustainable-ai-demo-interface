from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item.strip() for item in value if item.strip()]
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    app_env: str = Field("production", validation_alias="APP_ENV")
    app_public_url: str = Field("http://localhost:30080", validation_alias="APP_PUBLIC_URL")
    app_jwt_secret: str = Field(..., validation_alias="APP_JWT_SECRET")
    app_jwt_issuer: str = Field("sustainable-ai-demo-interface", validation_alias="APP_JWT_ISSUER")
    app_jwt_audience: str = Field("sustainable-ai-demo-users", validation_alias="APP_JWT_AUDIENCE")
    app_session_ttl_minutes: int = Field(120, validation_alias="APP_SESSION_TTL_MINUTES")
    app_admin_subjects: list[str] = Field(default_factory=list, validation_alias="APP_ADMIN_SUBJECTS")
    session_cookie_name: str = Field("sustainable_ai_session", validation_alias="SESSION_COOKIE_NAME")
    cors_allowed_origins: list[str] = Field(default_factory=list, validation_alias="CORS_ALLOWED_ORIGINS")
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")

    vc_jwt_validation_enabled: bool = Field(True, validation_alias="VC_JWT_VALIDATION_ENABLED")
    vc_jwt_validation_mock_mode: bool = Field(False, validation_alias="VC_JWT_VALIDATION_MOCK_MODE")
    vc_jwt_validation_url: str = Field(..., validation_alias="VC_JWT_VALIDATION_URL")
    vc_jwt_validation_timeout_seconds: float = Field(10.0, validation_alias="VC_JWT_VALIDATION_TIMEOUT_SECONDS")
    vc_jwt_validation_expected_compliant_field: str = Field(
        "compliant",
        validation_alias="VC_JWT_VALIDATION_EXPECTED_COMPLIANT_FIELD",
    )

    db_host: str = Field(..., validation_alias="DB_HOST")
    db_port: int = Field(5432, validation_alias="DB_PORT")
    db_name: str = Field(..., validation_alias="DB_NAME")
    db_user: str = Field(..., validation_alias="DB_USER")
    db_password: str = Field(..., validation_alias="DB_PASSWORD")
    db_sslmode: str = Field("require", validation_alias="DB_SSLMODE")

    demo_model_id: str = Field("sustainable-ai-model-v1", validation_alias="DEMO_MODEL_ID")
    demo_model_version: str = Field("v1.0", validation_alias="DEMO_MODEL_VERSION")
    demo_total_duration_seconds: int = Field(300, validation_alias="DEMO_TOTAL_DURATION_SECONDS")
    demo_enforce_phase_timing: bool = Field(True, validation_alias="DEMO_ENFORCE_PHASE_TIMING")
    demo_command_poll_interval_seconds: int = Field(5, validation_alias="DEMO_COMMAND_POLL_INTERVAL_SECONDS")
    demo_stream_interval_seconds: int = Field(2, validation_alias="DEMO_STREAM_INTERVAL_SECONDS")

    site_wiener_neustadt_location_name: str = Field("Wiener Neustadt", validation_alias="SITE_WIENER_NEUSTADT_LOCATION_NAME")
    site_wiener_neustadt_region_code: str = Field("region_2", validation_alias="SITE_WIENER_NEUSTADT_REGION_CODE")
    site_wien_location_name: str = Field("Wien", validation_alias="SITE_WIEN_LOCATION_NAME")
    site_wien_region_code: str = Field("region_1", validation_alias="SITE_WIEN_REGION_CODE")
    site_eisenstadt_location_name: str = Field("Eisenstadt", validation_alias="SITE_EISENSTADT_LOCATION_NAME")
    site_eisenstadt_region_code: str = Field("region_3", validation_alias="SITE_EISENSTADT_REGION_CODE")

    s3_bucket: str = Field("weather-data-intelligent-ai-training", validation_alias="S3_BUCKET")
    certificate_signing_secret: str | None = Field(None, validation_alias="CERTIFICATE_SIGNING_SECRET")
    certificate_issuer: str = Field("Sustainable AI Demo Interface", validation_alias="CERTIFICATE_ISSUER")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("cors_allowed_origins", "app_admin_subjects", mode="before")
    @classmethod
    def parse_csv_fields(cls, value: str | list[str] | None) -> list[str]:
        return _split_csv(value)

    @property
    def database_dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password} sslmode={self.db_sslmode}"
        )

    @property
    def cookie_secure(self) -> bool:
        return self.app_public_url.lower().startswith("https://")

    @property
    def mock_auth_visible(self) -> bool:
        return self.vc_jwt_validation_mock_mode


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, get_settings]

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = Field(default="production", alias="APP_ENV")
    app_public_url: str = Field(default="http://localhost:30080", alias="APP_PUBLIC_URL")
    app_jwt_secret: str = Field(default="change-me", alias="APP_JWT_SECRET")
    app_jwt_issuer: str = Field(default="sustainable-ai-demo-interface", alias="APP_JWT_ISSUER")
    app_jwt_audience: str = Field(default="sustainable-ai-demo-users", alias="APP_JWT_AUDIENCE")
    session_cookie_name: str = Field(default="sustainable_ai_session", alias="SESSION_COOKIE_NAME")
    session_ttl_minutes: int = Field(default=120, alias="SESSION_TTL_MINUTES")
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:30080"], alias="CORS_ALLOWED_ORIGINS")
    app_admin_subjects: list[str] = Field(default_factory=list, alias="APP_ADMIN_SUBJECTS")

    vc_jwt_validation_enabled: bool = Field(default=True, alias="VC_JWT_VALIDATION_ENABLED")
    vc_jwt_validation_mock_mode: bool = Field(default=False, alias="VC_JWT_VALIDATION_MOCK_MODE")
    vc_jwt_validation_url: str = Field(
        default="https://gxdch-nas-basic-functions.cloudcarib.com/api/jwt/compliance-verification",
        alias="VC_JWT_VALIDATION_URL",
    )
    vc_jwt_validation_timeout_seconds: int = Field(default=10, alias="VC_JWT_VALIDATION_TIMEOUT_SECONDS")
    vc_jwt_validation_expected_compliant_field: str = Field(default="compliant", alias="VC_JWT_VALIDATION_EXPECTED_COMPLIANT_FIELD")
    vc_jwt_validation_content_type: str = Field(default="application/vc+jwt", alias="VC_JWT_VALIDATION_CONTENT_TYPE")

    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="sustainable_ai_weather", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_sslmode: str = Field(default="require", alias="DB_SSLMODE")
    db_pool_min_size: int = Field(default=1, alias="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(default=8, alias="DB_POOL_MAX_SIZE")

    demo_model_id: str = Field(default="sustainable-ai-model-v1", alias="DEMO_MODEL_ID")
    demo_model_version: str = Field(default="v1.0", alias="DEMO_MODEL_VERSION")
    demo_total_duration_seconds: int = Field(default=300, alias="DEMO_TOTAL_DURATION_SECONDS")
    demo_enforce_phase_timing: bool = Field(default=True, alias="DEMO_ENFORCE_PHASE_TIMING")
    demo_command_poll_interval_seconds: int = Field(default=5, alias="DEMO_COMMAND_POLL_INTERVAL_SECONDS")
    demo_stream_interval_seconds: int = Field(default=2, alias="DEMO_STREAM_INTERVAL_SECONDS")
    demo_edge_command_type: str = Field(default="START_TRAINING", alias="DEMO_EDGE_COMMAND_TYPE")

    site_wiener_neustadt_location_name: str = Field(default="Wiener Neustadt", alias="SITE_WIENER_NEUSTADT_LOCATION_NAME")
    site_wiener_neustadt_region_code: str = Field(default="region_2", alias="SITE_WIENER_NEUSTADT_REGION_CODE")
    site_wien_location_name: str = Field(default="Wien", alias="SITE_WIEN_LOCATION_NAME")
    site_wien_region_code: str = Field(default="region_1", alias="SITE_WIEN_REGION_CODE")
    site_eisenstadt_location_name: str = Field(default="Eisenstadt", alias="SITE_EISENSTADT_LOCATION_NAME")
    site_eisenstadt_region_code: str = Field(default="region_3", alias="SITE_EISENSTADT_REGION_CODE")

    s3_bucket: str = Field(default="weather-data-intelligent-ai-training", alias="S3_BUCKET")

    @field_validator("cors_allowed_origins", "app_admin_subjects", mode="before")
    @classmethod
    def split_csv(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return list(value)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cookie_secure(self) -> bool:
        return self.app_public_url.lower().startswith("https://")

    @property
    def database_dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password} sslmode={self.db_sslmode}"
        )

    @property
    def phase_plan(self) -> list[dict[str, Any]]:
        return [
            {
                "phase_no": 1,
                "location_name": self.site_wiener_neustadt_location_name,
                "region_code": self.site_wiener_neustadt_region_code,
                "target_percent": 20,
                "target_duration_seconds": 60,
            },
            {
                "phase_no": 2,
                "location_name": self.site_wien_location_name,
                "region_code": self.site_wien_region_code,
                "target_percent": 30,
                "target_duration_seconds": 90,
            },
            {
                "phase_no": 3,
                "location_name": self.site_eisenstadt_location_name,
                "region_code": self.site_eisenstadt_region_code,
                "target_percent": 30,
                "target_duration_seconds": 90,
            },
            {
                "phase_no": 4,
                "location_name": self.site_wiener_neustadt_location_name,
                "region_code": self.site_wiener_neustadt_region_code,
                "target_percent": 20,
                "target_duration_seconds": 60,
            },
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 프로젝트 루트(.env 위치) — 실행 위치(cwd)와 무관하게 .env를 찾는다.
# config.py: backend/app/core/config.py → parents[3] = senior-jobs/
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # 루트 .env 를 먼저, backend/.env 가 있으면 그 값으로 덮어쓴다.
        env_file=(str(_PROJECT_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 앱 기본 ──────────────────────────────────────────────
    app_name: str = "Senior Jobs API"
    debug: bool = False
    allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # ── PostgreSQL ───────────────────────────────────────────
    # .env / docker-compose 와 동일한 컴포넌트 변수를 읽는다 (비밀값은 .env에서 주입)
    postgres_user: str = "senior_jobs_user"
    postgres_password: str = ""
    postgres_db: str = "senior_jobs"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    # 전체 URL을 직접 주입하면(docker-compose의 DATABASE_URL) 그 값을 우선 사용
    database_url: Optional[str] = None

    # ── Redis ────────────────────────────────────────────────
    redis_password: str = ""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: Optional[str] = None
    celery_broker_url: Optional[str] = None

    # ── MinIO ────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = ""
    # docker-compose는 MINIO_ACCESS_KEY/MINIO_SECRET_KEY 를 직접 주입하므로 그 값을 우선 사용
    minio_access_key: Optional[str] = None
    minio_secret_key: Optional[str] = None
    minio_bucket: str = "senior-jobs"
    minio_secure: bool = False

    # ── JWT ──────────────────────────────────────────────────
    secret_key: str = ""  # .env의 SECRET_KEY에서 주입 (필수)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ── Rate Limiting ────────────────────────────────────────
    rate_limit_per_minute: int = 60

    # ── 사업 운영 공통 ────────────────────────────────────────
    operation_months: int = 11          # 1~11월 (12월 입력 차단)
    adjustment_start_month: int = 7     # 공익활동형 점진 조정 시작월

    # ── 공익활동형 ────────────────────────────────────────────
    public_benefit_monthly_default: int = 30
    public_benefit_monthly_max: int = 42
    monthly_overtime_buffer: float = 1.0   # 42h + 1h까지 경고 허용
    public_benefit_total_hours: int = 330
    public_benefit_session_default: int = 3
    public_benefit_session_max: int = 4

    # ── 사회서비스형 ──────────────────────────────────────────
    social_service_monthly_default: int = 60
    social_service_monthly_max: int = 60
    social_service_total_hours: int = 660
    social_service_session_default: int = 3
    social_service_session_max: int = 8    # 근로기준법

    # ── 시장형 ───────────────────────────────────────────────
    market_session_max: int = 8            # 근로기준법 고정

    @model_validator(mode="after")
    def _compose_connection_urls(self) -> "Settings":
        """전체 URL이 직접 주입되지 않았으면 컴포넌트 변수로부터 조립한다.

        - docker-compose: DATABASE_URL 등을 직접 주입 → 그 값 사용
        - 로컬 직접 실행: .env의 POSTGRES_PASSWORD 등으로 조립
        """
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        if not self.redis_url:
            self.redis_url = (
                f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
            )
        if not self.celery_broker_url:
            self.celery_broker_url = (
                f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/1"
            )
        if not self.minio_access_key:
            self.minio_access_key = self.minio_root_user
        if not self.minio_secret_key:
            self.minio_secret_key = self.minio_root_password
        return self


# 사업단 유형별 기본값 (TYPE_DEFAULTS)
TYPE_DEFAULTS: dict[str, dict] = {
    "public_benefit": {
        "monthly_default_hours": 30,
        "monthly_max_hours": 42,
        "total_annual_hours": 330,
        "session_default_hours": 3,
        "session_max_hours": 4,
        "carry_over_enabled": True,
    },
    "social_service": {
        "monthly_default_hours": 60,
        "monthly_max_hours": 60,
        "total_annual_hours": 660,
        "session_default_hours": 3,
        "session_max_hours": 8,
        "carry_over_enabled": False,
    },
    "market": {
        "monthly_default_hours": None,   # TENANT_ADMIN 필수 입력
        "monthly_max_hours": None,
        "total_annual_hours": None,
        "session_default_hours": None,
        "session_max_hours": 8,          # 고정
        "carry_over_enabled": False,
    },
}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

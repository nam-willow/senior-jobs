from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import close_redis
from app.core.logging import RequestLoggingMiddleware, setup_logging
# noqa: F401 — Base.metadata 등록
from app.models import audit_log, tenant, user  # noqa: F401
from app.models import (  # noqa: F401
    business_unit, senior, monthly_work_records,
    consultation_log, annual_budget, budget_expenditure,
    policy_rule, user_business_unit,
    document_snapshot, generated_file,
)
from app.routers import (
    auth, seniors, tenants, users, business_units,
    work_records, budgets, consultation_logs,
    audit_logs, policy_rules, dashboard,
    work_logs, tasks,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield
    await close_redis()


limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ── 미들웨어 ──────────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ── 라우터 ────────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth.router,              prefix=PREFIX)
app.include_router(tenants.router,           prefix=PREFIX)
app.include_router(users.router,             prefix=PREFIX)
app.include_router(business_units.router,    prefix=PREFIX)
app.include_router(seniors.router,           prefix=PREFIX)
app.include_router(work_records.router,      prefix=PREFIX)
app.include_router(budgets.router,           prefix=PREFIX)
app.include_router(consultation_logs.router, prefix=PREFIX)
app.include_router(audit_logs.router,        prefix=PREFIX)
app.include_router(policy_rules.router,      prefix=PREFIX)
app.include_router(dashboard.router,         prefix=PREFIX)
app.include_router(work_logs.router,         prefix=PREFIX)
app.include_router(tasks.router,             prefix=PREFIX)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}

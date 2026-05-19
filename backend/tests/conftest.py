from __future__ import annotations
"""
pytest fixtures — 인메모리 SQLite 대신 실제 asyncpg 사용.
테스트 DB: senior_jobs_test (docker-compose postgres 컨테이너 재사용)
"""
import asyncio
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db, get_redis
from app.core.security import hash_password
from app.models.audit_log import AuditLog  # noqa: F401 — Base.metadata 등록용
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User, UserRole

# ── 테스트 DB URL ─────────────────────────────────────────────────────────────
TEST_DB_URL = settings.database_url.rsplit("/", 1)[0] + "/senior_jobs_test"

# NullPool: 각 픽스처가 독립 커넥션을 받아 pool dirty-state 문제를 방지
test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.run_sync(Base.metadata.drop_all)
        # drop_all removes tables but not ENUM types — recreate them
        for enum_name in ("userrole",):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
        await conn.execute(text(
            "CREATE TYPE userrole AS ENUM "
            "('platform_admin','tenant_admin','social_worker','approver','auditor','viewer')"
        ))
        await conn.run_sync(Base.metadata.create_all)
        # create non-privileged role for RLS integration tests
        # (superusers bypass RLS even with FORCE; app_role does not)
        await conn.execute(text(
            "DO $$ BEGIN CREATE ROLE app_role; "
            "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
        ))
        await conn.execute(text("GRANT SELECT ON users, tenants TO app_role"))
        # create_all does not add RLS — apply tenant isolation policy manually
        for table in ("tenants", "users", "audit_logs"):
            await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            await conn.execute(text(f"ALTER TABLE {table} FORCE  ROW LEVEL SECURITY"))
            await conn.execute(text(
                f"CREATE POLICY tenant_isolation ON {table} "
                f"USING (current_setting('app.current_tenant', true) = 'ALL' "
                f"OR tenant_id::text = current_setting('app.current_tenant', true))"
                if table != "tenants" else
                f"CREATE POLICY tenant_isolation ON {table} "
                f"USING (current_setting('app.current_tenant', true) = 'ALL' "
                f"OR id::text = current_setting('app.current_tenant', true))"
            ))
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TYPE IF EXISTS userrole CASCADE"))


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        await session.execute(text("SET LOCAL app.current_tenant = 'ALL'"))
        yield session
        await session.rollback()


@pytest.fixture
def redis_mock():
    """Redis를 mock으로 대체 — 단위 테스트용."""
    store: dict = {}

    mock = AsyncMock()

    async def setex(key, ttl, value):
        store[key] = value

    async def get(key):
        return store.get(key)

    async def delete(*keys):
        for k in keys:
            store.pop(k, None)

    async def sadd(key, *values):
        store.setdefault(key, set()).update(values)

    async def srem(key, *values):
        if key in store:
            store[key].discard(*values)

    async def smembers(key):
        return store.get(key, set())

    async def expire(key, ttl):
        pass

    class Pipeline:
        def __init__(self):
            self._cmds = []

        def setex(self, key, ttl, value):
            self._cmds.append(("setex", key, ttl, value))
            return self

        def get(self, key):
            self._cmds.append(("get", key))
            return self

        def delete(self, *keys):
            self._cmds.append(("delete", *keys))
            return self

        def sadd(self, key, *values):
            self._cmds.append(("sadd", key, *values))
            return self

        def srem(self, key, *values):
            self._cmds.append(("srem", key, *values))
            return self

        def expire(self, key, ttl):
            self._cmds.append(("expire", key, ttl))
            return self

        async def execute(self):
            results = []
            for cmd in self._cmds:
                op = cmd[0]
                if op == "setex":
                    await setex(cmd[1], cmd[2], cmd[3])
                elif op == "delete":
                    await delete(*cmd[1:])
                elif op == "sadd":
                    await sadd(cmd[1], *cmd[2:])
                elif op == "srem":
                    await srem(cmd[1], *cmd[2:])
                results.append(None)
            return results

    mock.setex = setex
    mock.get = get
    mock.delete = delete
    mock.sadd = sadd
    mock.srem = srem
    mock.smembers = smembers
    mock.expire = expire
    mock.pipeline = lambda: Pipeline()
    mock._store = store
    return mock


@pytest_asyncio.fixture
async def test_tenant_id(db: AsyncSession) -> str:
    tenant = Tenant(
        tenant_code=f"T{uuid.uuid4().hex[:6]}",
        name="테스트기관",
        subscription_plan="basic",
        is_active=True,
    )
    db.add(tenant)
    await db.flush()
    return str(tenant.id)


@pytest_asyncio.fixture
async def test_user(db: AsyncSession, test_tenant_id: str) -> User:
    user = User(
        tenant_id=uuid.UUID(test_tenant_id),
        name="테스트유저",
        email=f"user_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("Test1234!"),
        role=UserRole.SOCIAL_WORKER,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


def make_app(db_session: AsyncSession, redis_mock) -> FastAPI:
    from app.routers.auth import router as auth_router
    from app.core.logging import RequestLoggingMiddleware, setup_logging
    setup_logging()
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: redis_mock
    return app

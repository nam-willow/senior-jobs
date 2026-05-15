"""
TC-AUTH-06: RBAC 403 차단
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert

from app.core.database import Base
from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole
from tests.conftest import make_app


@pytest_asyncio.fixture
async def viewer_token(db, test_tenant_id):
    user = User(
        tenant_id=uuid.UUID(test_tenant_id),
        name="뷰어",
        email=f"viewer_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("Test1234!"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return create_access_token(
        user_id=str(user.id),
        tenant_id=test_tenant_id,
        role=UserRole.VIEWER.value,
    )


@pytest.mark.asyncio
async def test_rbac_403_block(db, redis_mock, viewer_token):
    """VIEWER가 TENANT_ADMIN 전용 엔드포인트 접근 시 403."""
    from fastapi import FastAPI, Depends
    from app.core.permissions import RequireTenantAdmin, CurrentUser

    app = make_app(db, redis_mock)

    @app.get("/api/v1/admin-only")
    async def admin_only(user: CurrentUser = RequireTenantAdmin):
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get(
            "/api/v1/admin-only",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
    assert resp.status_code == 403

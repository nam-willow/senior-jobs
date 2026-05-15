"""
TC-AUTH-07: Tenant Isolation — A기관이 B기관 데이터 접근 불가 (RLS 검증)
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole


@pytest_asyncio.fixture
async def two_tenants(db):
    tenant_a = Tenant(tenant_code=f"A{uuid.uuid4().hex[:6]}", name="기관A", subscription_plan="basic", is_active=True)
    tenant_b = Tenant(tenant_code=f"B{uuid.uuid4().hex[:6]}", name="기관B", subscription_plan="basic", is_active=True)
    db.add_all([tenant_a, tenant_b])
    await db.flush()

    user_a = User(
        tenant_id=tenant_a.id, name="유저A",
        email=f"a_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("Test1234!"),
        role=UserRole.SOCIAL_WORKER, is_active=True,
    )
    user_b = User(
        tenant_id=tenant_b.id, name="유저B",
        email=f"b_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("Test1234!"),
        role=UserRole.SOCIAL_WORKER, is_active=True,
    )
    db.add_all([user_a, user_b])
    await db.flush()
    return str(tenant_a.id), str(tenant_b.id), user_a, user_b


@pytest.mark.asyncio
async def test_tenant_isolation_cross_access(db, two_tenants):
    """
    RLS: tenant_id = A로 세션 설정 후 users 조회 시 B의 유저는 보이지 않아야 함.
    """
    tenant_a_id, tenant_b_id, user_a, user_b = two_tenants

    # A 기관 컨텍스트로 전환
    await db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_a_id}'"))

    result = await db.execute(select(User))
    visible_users = result.scalars().all()
    visible_ids = {str(u.id) for u in visible_users}

    # A 기관 유저는 보여야 함
    assert str(user_a.id) in visible_ids
    # B 기관 유저는 안 보여야 함
    assert str(user_b.id) not in visible_ids

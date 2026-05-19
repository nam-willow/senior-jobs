from __future__ import annotations
"""
개발/테스트용 초기 데이터 삽입.
운영 환경에서는 절대 실행 금지.

실행: python -m app.seed
"""
import asyncio
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole


async def _seed(db: AsyncSession) -> None:
    await db.execute(text("SET LOCAL app.current_tenant = 'ALL'"))

    # 중복 실행 방지
    existing = await db.execute(select(Tenant).where(Tenant.tenant_code == "DEMO"))
    if existing.scalar_one_or_none() is not None:
        print("✓  seed 데이터 이미 존재 — 건너뜀")
        return

    # ── 1. 기본 테넌트 ─────────────────────────────────────────────────────────
    tenant = Tenant(
        id=uuid.uuid4(),
        tenant_code="DEMO",
        name="데모 기관",
        subscription_plan="basic",
        is_active=True,
    )
    db.add(tenant)
    await db.flush()

    # ── 2. platform_admin ──────────────────────────────────────────────────────
    db.add(User(
        tenant_id=tenant.id,
        name="플랫폼 관리자",
        email="admin@senior-jobs.local",
        password_hash=hash_password("Admin1234!"),
        role=UserRole.PLATFORM_ADMIN,
        is_active=True,
    ))

    # ── 3. tenant_admin ────────────────────────────────────────────────────────
    db.add(User(
        tenant_id=tenant.id,
        name="기관 관리자",
        email="tenant@senior-jobs.local",
        password_hash=hash_password("Admin1234!"),
        role=UserRole.TENANT_ADMIN,
        is_active=True,
    ))

    # ── 4. social_worker ───────────────────────────────────────────────────────
    db.add(User(
        tenant_id=tenant.id,
        name="사회복지사1",
        email="worker@senior-jobs.local",
        password_hash=hash_password("Worker1234!"),
        role=UserRole.SOCIAL_WORKER,
        is_active=True,
    ))

    await db.commit()
    print("✓  seed 완료")
    print("   admin@senior-jobs.local  / Admin1234!")
    print("   tenant@senior-jobs.local / Admin1234!")
    print("   worker@senior-jobs.local / Worker1234!")


async def main() -> None:
    if not settings.debug:
        print("⛔  debug=False 환경에서는 seed를 실행할 수 없습니다.")
        return
    async with AsyncSessionLocal() as db:
        await _seed(db)


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations
"""
TenantMiddleware:
  JWT payload의 tenant_id를 추출 → DB 세션에
  SET LOCAL app.current_tenant = '{tenant_id}' 주입 → PostgreSQL RLS 자동 적용.

platform_admin은 'ALL'을 주입하여 RLS 우회.
"""
from collections.abc import AsyncGenerator
from typing_extensions import Annotated

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import CurrentUser, Role, get_current_user

_PLATFORM_BYPASS = "ALL"


async def get_tenant_db(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncGenerator[AsyncSession, None]:
    """
    RLS 컨텍스트가 주입된 DB 세션을 반환하는 의존성.
    platform_admin → 'ALL' (RLS 우회)
    그 외 → JWT tenant_id
    """
    tenant_value = (
        _PLATFORM_BYPASS
        if current_user.is_platform_admin
        else current_user.tenant_id
    )
    await db.execute(
        text("SET LOCAL app.current_tenant = :tenant_id"),
        {"tenant_id": tenant_value},
    )
    yield db


async def get_tenant_db_raw(
    tenant_id: str,
    db: AsyncSession,
) -> None:
    """
    서비스 레이어에서 직접 tenant 컨텍스트를 주입할 때 사용.
    (Celery worker 등 HTTP 요청 컨텍스트 없는 환경)
    """
    await db.execute(
        text("SET LOCAL app.current_tenant = :tenant_id"),
        {"tenant_id": tenant_id},
    )

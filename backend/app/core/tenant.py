from __future__ import annotations
"""
TenantMiddleware:
  JWT payload의 tenant_id를 추출 → DB 세션에
  SET app.current_tenant = '{tenant_id}' 주입 → PostgreSQL RLS 자동 적용.

platform_admin은 'ALL'을 주입하여 RLS 우회.

NOTE: PostgreSQL SET 명령은 바인딩 파라미터($1)를 지원하지 않으므로
      tenant_value를 SQL 문자열에 직접 포함시킨다.
      tenant_value는 'ALL' 또는 JWT 검증된 UUID (안전한 값)이다.
"""
import re
from collections.abc import AsyncGenerator
from typing_extensions import Annotated

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import CurrentUser, Role, get_current_user

_PLATFORM_BYPASS = "ALL"
_UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _safe_tenant_value(value: str) -> str:
    if value == _PLATFORM_BYPASS or _UUID_PATTERN.match(value):
        return value
    raise ValueError(f"Invalid tenant value: {value!r}")


async def get_tenant_db(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncGenerator[AsyncSession, None]:
    """
    RLS 컨텍스트가 주입된 DB 세션을 반환하는 의존성.
    platform_admin → 'ALL' (RLS 우회)
    그 외 → JWT tenant_id
    """
    tenant_value = _safe_tenant_value(
        _PLATFORM_BYPASS
        if current_user.is_platform_admin
        else current_user.tenant_id
    )
    await db.execute(text(f"SET app.current_tenant = '{tenant_value}'"))
    yield db


async def get_tenant_db_raw(
    tenant_id: str,
    db: AsyncSession,
) -> None:
    """
    서비스 레이어에서 직접 tenant 컨텍스트를 주입할 때 사용.
    (Celery worker 등 HTTP 요청 컨텍스트 없는 환경)
    """
    tenant_value = _safe_tenant_value(tenant_id)
    await db.execute(text(f"SET app.current_tenant = '{tenant_value}'"))

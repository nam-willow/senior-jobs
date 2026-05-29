from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, require_permission
from app.models.audit_log import AuditLog
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


class AuditLogResponse:
    pass


from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    action_type: str
    target_table: str
    target_id: Optional[uuid.UUID]
    ip_address: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=PaginatedResponse[AuditLogOut])
async def list_audit_logs(
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_AUDIT_LOG"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    target_table: Optional[str] = None,
    user_id: Optional[str] = None,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
):
    """
    [감사 로그 목록] 기관 내 데이터 변경 이력 조회. 최대 200건, 생성일 내림차순.
    설정 페이지 감사 로그 탭에서 사용. VIEW_AUDIT_LOG 권한 필요.

    Args:
        target_table (str, optional)      : 대상 테이블 필터.
                                            예) "seniors" | "users" | "work_records"
        user_id      (str, optional)      : 특정 직원 UUID로 필터.
        from_dt      (str, optional)      : 조회 시작 일시. 형식: "YYYY-MM-DDTHH:MM:SS"
        to_dt        (str, optional)      : 조회 종료 일시. 형식: "YYYY-MM-DDTHH:MM:SS"

    Returns:
        items (List[AuditLogOut]) : 감사 로그 목록.
            - action_type  (str)      : 작업 유형. "CREATE" | "UPDATE" | "DELETE"
            - target_table (str)      : 변경된 테이블명.
            - target_id    (str|null) : 변경된 레코드 UUID.
            - ip_address   (str)      : 작업자 IP 주소.
            - created_at   (str)      : 작업 일시.
        total (int) : 반환된 건수 (최대 200).

    Raises:
        401 : 토큰 없음 또는 만료
        403 : VIEW_AUDIT_LOG 권한 없음
    """
    q = select(AuditLog).where(
        AuditLog.tenant_id == uuid.UUID(current_user.tenant_id)
    ).execution_options(include_deleted=True)

    if target_table:
        q = q.where(AuditLog.target_table == target_table)
    if user_id:
        q = q.where(AuditLog.user_id == uuid.UUID(user_id))
    if from_dt:
        q = q.where(AuditLog.created_at >= from_dt)
    if to_dt:
        q = q.where(AuditLog.created_at <= to_dt)

    result = await db.execute(q.order_by(AuditLog.created_at.desc()).limit(200))
    items = list(result.scalars().all())
    return {"items": items, "total": len(items)}

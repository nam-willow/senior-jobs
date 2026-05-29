from __future__ import annotations
import uuid
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, require_permission
from app.models.policy_rule import PolicyRule, PolicyVersion
from app.schemas.common import PaginatedResponse
from app.schemas.policy_rule import PolicyRuleCreate, PolicyRuleResponse, PolicyRuleUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/policy-rules", tags=["policy-rules"])


@router.get("/", response_model=PaginatedResponse[PolicyRuleResponse])
async def list_policy_rules(
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_POLICY"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [정책 규칙 목록] 기관의 정책 규칙 전체 조회. priority 오름차순 정렬.
    설정 페이지 정책 탭에서 사용. MANAGE_POLICY 권한 필요.

    Args:
        없음 (토큰에서 tenant_id 자동 추출)

    Returns:
        items (List[PolicyRuleResponse]) : 정책 규칙 목록.
            - rule_code      (str)      : 규칙 코드.
            - rule_name      (str)      : 규칙명.
            - priority       (int)      : 우선순위. 낮을수록 먼저 적용.
            - is_active      (bool)     : 활성화 여부.
            - effective_from (str)      : 적용 시작일. 형식: "YYYY-MM-DD"
            - effective_to   (str|null) : 적용 종료일.
            - condition_json (object)   : 적용 조건 JSON.
            - action_json    (object)   : 적용 액션 JSON.
        total (int) : 전체 건수.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_POLICY 권한 없음
    """
    result = await db.execute(
        select(PolicyRule)
        .where(PolicyRule.tenant_id == uuid.UUID(current_user.tenant_id))
        .order_by(PolicyRule.priority)
    )
    items = list(result.scalars().all())
    return {"items": items, "total": len(items)}


@router.post("/", response_model=PolicyRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_rule(
    data: PolicyRuleCreate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_POLICY"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [정책 규칙 생성] 새 정책 규칙 등록. 생성 시 버전 스냅샷(PolicyVersion) 자동 저장.
    감사 로그(IP 포함) 기록.

    Args:
        data.rule_code      (str)          : 규칙 고유 코드. 필수. 예) "OVERTIME_WARNING"
        data.rule_name      (str)          : 규칙명. 필수.
        data.priority       (int)          : 우선순위. 기본값 0. 낮을수록 먼저 적용.
        data.effective_from (str, date)    : 적용 시작일. 필수. 형식: "YYYY-MM-DD"
        data.effective_to   (str, optional): 적용 종료일. 형식: "YYYY-MM-DD"
        data.condition_json (object)       : 적용 조건 JSON. 필수.
        data.action_json    (object)       : 적용 액션 JSON. 필수.

    Returns:
        PolicyRuleResponse : 생성된 정책 규칙.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_POLICY 권한 없음
        422 : 필수 항목 누락
    """
    rule = PolicyRule(
        tenant_id=uuid.UUID(current_user.tenant_id),
        rule_code=data.rule_code,
        rule_name=data.rule_name,
        priority=data.priority,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        condition_json=data.condition_json,
        action_json=data.action_json,
    )
    db.add(rule)
    await db.flush()
    # 버전 스냅샷 저장
    db.add(PolicyVersion(
        policy_rule_id=rule.id,
        tenant_id=uuid.UUID(current_user.tenant_id),
        snapshot_json=data.model_dump(mode="json"),
        changed_by=uuid.UUID(current_user.user_id),
    ))
    await record_audit(
        db, tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        action_type="CREATE", target_table="policy_rules",
        target_id=str(rule.id),
        after_data={"rule_code": data.rule_code},
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=PolicyRuleResponse)
async def update_policy_rule(
    rule_id: uuid.UUID,
    data: PolicyRuleUpdate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_POLICY"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [정책 규칙 수정] 기존 정책 규칙 부분 수정. 수정 시 버전 스냅샷 자동 저장.
    감사 로그(IP 포함) 기록. 전달하지 않은 필드는 기존 값 유지.

    Args:
        rule_id              (str, path)    : 수정할 정책 규칙 UUID.
        data.rule_name       (str, optional): 변경할 규칙명.
        data.priority        (int, optional): 변경할 우선순위.
        data.is_active       (bool,optional): 활성화 여부.
        data.effective_to    (str, optional): 변경할 적용 종료일. 형식: "YYYY-MM-DD"
        data.condition_json  (obj, optional): 변경할 조건 JSON.
        data.action_json     (obj, optional): 변경할 액션 JSON.

    Returns:
        PolicyRuleResponse : 수정된 정책 규칙.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_POLICY 권한 없음
        404 : 정책 규칙 없음
    """
    result = await db.execute(
        select(PolicyRule).where(
            PolicyRule.id == rule_id,
            PolicyRule.tenant_id == uuid.UUID(current_user.tenant_id),
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy rule not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    # 버전 스냅샷
    from sqlalchemy.orm import object_session
    db.add(PolicyVersion(
        policy_rule_id=rule.id,
        tenant_id=uuid.UUID(current_user.tenant_id),
        snapshot_json=data.model_dump(mode="json", exclude_unset=True),
        changed_by=uuid.UUID(current_user.user_id),
    ))
    await record_audit(
        db, tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        action_type="UPDATE", target_table="policy_rules",
        target_id=str(rule_id),
        after_data=data.model_dump(exclude_unset=True, mode="json"),
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_rule(
    rule_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_POLICY"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [정책 규칙 삭제] 정책 규칙 비활성화 (is_active=False 소프트 삭제).
    감사 로그(IP 포함) 기록.

    Args:
        rule_id (str, path) : 삭제할 정책 규칙 UUID.

    Returns:
        없음 (HTTP 204 No Content)

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_POLICY 권한 없음
        404 : 정책 규칙 없음
    """
    result = await db.execute(
        select(PolicyRule).where(
            PolicyRule.id == rule_id,
            PolicyRule.tenant_id == uuid.UUID(current_user.tenant_id),
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy rule not found")
    rule.is_active = False
    await record_audit(
        db, tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        action_type="DELETE", target_table="policy_rules",
        target_id=str(rule_id),
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()

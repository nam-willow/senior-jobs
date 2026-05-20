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

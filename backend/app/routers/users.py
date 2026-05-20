from __future__ import annotations
import uuid
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, RequireTenantAdmin, require_permission
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.user_business_unit import UserBusinessUnit
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    result = await db.execute(
        select(User).where(User.tenant_id == uuid.UUID(current_user.tenant_id))
    )
    items = list(result.scalars().all())
    return {"items": items, "total": len(items)}


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_USERS"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    user = User(
        tenant_id=uuid.UUID(current_user.tenant_id),
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    for bu_id in data.business_unit_ids:
        db.add(UserBusinessUnit(user_id=user.id, business_unit_id=bu_id))

    await record_audit(
        db, tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        action_type="CREATE", target_table="users",
        target_id=str(user.id), after_data={"email": data.email, "role": data.role.value},
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == uuid.UUID(current_user.tenant_id),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_USERS"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == uuid.UUID(current_user.tenant_id),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_fields = data.model_dump(exclude_unset=True, exclude={"business_unit_ids"})
    for field, value in update_fields.items():
        setattr(user, field, value)

    if data.business_unit_ids is not None:
        # 기존 배정 삭제 후 재등록
        existing = await db.execute(
            select(UserBusinessUnit).where(UserBusinessUnit.user_id == user_id)
        )
        for row in existing.scalars():
            await db.delete(row)
        for bu_id in data.business_unit_ids:
            db.add(UserBusinessUnit(user_id=user_id, business_unit_id=bu_id))

    await record_audit(
        db, tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        action_type="UPDATE", target_table="users", target_id=str(user_id),
        after_data=update_fields,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_USERS"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == uuid.UUID(current_user.tenant_id),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    await record_audit(
        db, tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        action_type="DELETE", target_table="users", target_id=str(user_id),
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()

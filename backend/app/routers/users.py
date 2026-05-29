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

from pydantic import BaseModel

class TransferAdminRequest(BaseModel):
    target_user_id: uuid.UUID

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [직원 목록] 해당 기관 소속 전체 직원 목록 조회. TENANT_ADMIN 전용.

    Args:
        없음 (토큰에서 tenant_id 자동 추출)

    Returns:
        items (List[UserResponse]) : 직원 목록.
            - id           (str)       : 직원 UUID.
            - name         (str)       : 이름.
            - email        (str)       : 이메일.
            - role         (str)       : 권한. "tenant_admin" | "social_worker"
            - is_active    (bool)      : 활성화 여부.
            - last_login_at(str|null)  : 마지막 로그인 일시.
        total (int) : 전체 건수.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : TENANT_ADMIN 권한 없음
    """
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
    """
    [직원 등록] 새 직원 계정 생성 + 사업단 배정. 감사 로그(IP 포함) 기록.

    Args:
        data.name             (str)       : 직원 이름. 필수.
        data.email            (str)       : 이메일 (로그인 ID). 필수. 기관 내 중복 불가.
        data.password         (str)       : 초기 비밀번호. 필수. 내부에서 bcrypt 해시 처리.
        data.role             (str)       : 권한. 필수.
                                            "tenant_admin" | "social_worker"
        data.business_unit_ids(List[str]) : 배정할 사업단 UUID 목록. 생략 시 빈 배열.

    Returns:
        UserResponse : 생성된 직원 정보.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_USERS 권한 없음
        422 : 필수 항목 누락
    """
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
    """
    [직원 상세] 특정 직원의 상세 정보 단건 조회. TENANT_ADMIN 전용.

    Args:
        user_id (str, path) : 조회할 직원 UUID.

    Returns:
        UserResponse : 직원 상세 정보.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : TENANT_ADMIN 권한 없음
        404 : 해당 기관에 존재하지 않는 직원
    """
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
    """
    [직원 수정] 직원 정보 및 사업단 배정 수정. 감사 로그(IP 포함) 기록.
    business_unit_ids 전달 시 기존 배정 전체 삭제 후 재등록 (교체 방식).

    Args:
        user_id                 (str, path)    : 수정할 직원 UUID.
        data.name               (str, optional): 변경할 이름.
        data.role               (str, optional): 변경할 권한. "tenant_admin" | "social_worker"
        data.is_active          (bool,optional): 변경할 활성화 여부.
        data.business_unit_ids  (List[str],opt): 새 사업단 배정 목록. 전달 시 기존 배정 전체 교체.

    Returns:
        UserResponse : 수정된 직원 정보.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_USERS 권한 없음
        404 : 직원 없음
    """
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


@router.patch("/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_USERS"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [직원 비활성화] 직원 계정을 비활성화하여 로그인 차단. 감사 로그(IP 포함) 기록.
    본인 계정은 비활성화 불가. 이미 비활성화된 계정도 불가.

    Args:
        user_id (str, path) : 비활성화할 직원 UUID.

    Returns:
        없음 (HTTP 204 No Content)

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_USERS 권한 없음
        404 : 직원 없음
        400 : 본인 계정이거나 이미 비활성화된 계정
    """
    if str(user_id) == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="본인 계정은 비활성화할 수 없습니다.",
        )
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == uuid.UUID(current_user.tenant_id),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 비활성화된 계정입니다.",
        )
    user.is_active = False
    await record_audit(
        db, tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        action_type="UPDATE", target_table="users", target_id=str(user_id),
        after_data={"is_active": False, "reason": "deactivated_by_admin"},
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()


@router.post("/transfer-admin", status_code=status.HTTP_204_NO_CONTENT)
async def transfer_admin(
    data: TransferAdminRequest,
    request: Request,
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [관리자 권한 이전] 현재 관리자를 사회복지사로 강등하고 대상 직원을 관리자로 승격.
    TENANT_ADMIN 전용. 감사 로그(IP 포함) 기록.
    본인에게 이전 불가. 비활성화된 계정으로 이전 불가.

    Args:
        data.target_user_id (str) : 관리자 권한을 받을 직원 UUID. 필수.

    Returns:
        없음 (HTTP 204 No Content)

    Raises:
        401 : 토큰 없음 또는 만료
        403 : TENANT_ADMIN 권한 없음
        400 : 본인에게 이전 시도
        404 : 대상 직원 없음 또는 비활성화 상태
    """
    if str(data.target_user_id) == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="본인에게 권한을 이전할 수 없습니다.",
        )
    result = await db.execute(
        select(User).where(
            User.id == data.target_user_id,
            User.tenant_id == uuid.UUID(current_user.tenant_id),
            User.is_active.is_(True),
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대상 직원을 찾을 수 없거나 비활성화된 계정입니다.",
        )

    # 현재 관리자 → 사회복지사로 강등
    me_result = await db.execute(
        select(User).where(User.id == uuid.UUID(current_user.user_id))
    )
    me = me_result.scalar_one()
    me.role = UserRole.SOCIAL_WORKER

    # 대상 → 관리자로 승격
    target.role = UserRole.TENANT_ADMIN

    await record_audit(
        db, tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        action_type="UPDATE", target_table="users", target_id=str(data.target_user_id),
        after_data={"role": "tenant_admin", "transferred_from": current_user.user_id},
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_USERS"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [직원 삭제] 직원 계정 삭제 처리 (is_active=False). 감사 로그(IP 포함) 기록.

    Args:
        user_id (str, path) : 삭제할 직원 UUID.

    Returns:
        없음 (HTTP 204 No Content)

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_USERS 권한 없음
        404 : 직원 없음
    """
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

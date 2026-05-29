from __future__ import annotations
import uuid
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, RequirePlatform
from app.models.tenant import Tenant
from app.schemas.common import PaginatedResponse
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    current_user: Annotated[CurrentUser, RequirePlatform],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [기관 목록] 플랫폼 전체 기관(테넌트) 목록 조회. 생성일 내림차순 정렬.
    플랫폼 관리자 전용. 슈퍼어드민 대시보드에서 사용.

    Args:
        없음 (토큰에서 platform_admin 권한 자동 확인)

    Returns:
        items (List[TenantResponse]) : 기관 목록.
            - id                (str)      : 기관 UUID.
            - tenant_code       (str)      : 기관 고유 코드.
            - name              (str)      : 기관명.
            - business_number   (str)      : 사업자 번호.
            - subscription_plan (str)      : 구독 플랜.
            - is_active         (bool)     : 활성화 여부.
            - created_at        (str)      : 생성 일시.
        total (int) : 전체 기관 수.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : platform_admin 권한 없음
    """
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    items = list(result.scalars().all())
    return {"items": items, "total": len(items)}


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    current_user: Annotated[CurrentUser, RequirePlatform],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [기관 등록] 새 기관(테넌트) 생성. 플랫폼 관리자 전용.
    신규 복지관·기관 온보딩 시 사용.

    Args:
        data.tenant_code       (str) : 기관 고유 코드. 필수. 예) "org-001"
        data.name              (str) : 기관명. 필수. 예) "행복복지관"
        data.business_number   (str) : 사업자 번호. 필수. 예) "123-45-67890"
        data.subscription_plan (str) : 구독 플랜. 필수. 예) "basic" | "standard" | "enterprise"

    Returns:
        TenantResponse : 생성된 기관 정보.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : platform_admin 권한 없음
        422 : 필수 항목 누락
    """
    tenant = Tenant(
        tenant_code=data.tenant_code,
        name=data.name,
        business_number=data.business_number,
        subscription_plan=data.subscription_plan,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    data: TenantUpdate,
    current_user: Annotated[CurrentUser, RequirePlatform],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [기관 수정] 기존 기관 정보 부분 수정. 플랫폼 관리자 전용.
    전달하지 않은 필드는 기존 값 유지.

    Args:
        tenant_id              (str, path)    : 수정할 기관 UUID.
        data.name              (str, optional): 변경할 기관명.
        data.business_number   (str, optional): 변경할 사업자 번호.
        data.subscription_plan (str, optional): 변경할 구독 플랜.
        data.is_active         (bool,optional): 변경할 활성화 여부.

    Returns:
        TenantResponse : 수정된 기관 정보.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : platform_admin 권한 없음
        404 : 기관 없음
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: uuid.UUID,
    current_user: Annotated[CurrentUser, RequirePlatform],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [기관 비활성화] 기관을 비활성화하여 로그인 차단 (is_active=False 소프트 삭제).
    플랫폼 관리자 전용. 실제 데이터는 삭제되지 않음.

    Args:
        tenant_id (str, path) : 비활성화할 기관 UUID.

    Returns:
        없음 (HTTP 204 No Content)

    Raises:
        401 : 토큰 없음 또는 만료
        403 : platform_admin 권한 없음
        404 : 기관 없음
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant.is_active = False
    await db.commit()

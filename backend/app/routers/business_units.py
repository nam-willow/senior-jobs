from __future__ import annotations
import uuid
from typing import Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, RequireTenantAdmin, require_permission
from app.schemas.business_unit import BusinessUnitCreate, BusinessUnitResponse, BusinessUnitUpdate
from app.schemas.common import PaginatedResponse
from app.services import business_unit_service

router = APIRouter(prefix="/business-units", tags=["business-units"])


@router.get("/", response_model=PaginatedResponse[BusinessUnitResponse])
async def list_business_units(
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    type: Optional[str] = None,
    year: Optional[int] = None,
):
    """
    [사업단 목록] 활성화된 사업단 목록 조회. 유형·연도 필터 지원.
    어르신 관리·근무 입력·예산·설정 등 여러 페이지에서 공통 사용.

    Args:
        type (str, optional) : 사업단 유형 필터.
                               "public_benefit" | "social_service" | "market"
        year (int, optional) : 사업 연도 필터. 예) 2026

    Returns:
        items (List[BusinessUnitResponse]) : 활성 사업단 목록.
            - id                   (str)  : 사업단 UUID.
            - name                 (str)  : 사업단명.
            - type                 (str)  : 유형.
            - year                 (int)  : 사업 연도.
            - monthly_default_hours(int)  : 월 기본 근무시간.
            - monthly_max_hours    (int)  : 월 최대 근무시간.
            - total_annual_hours   (int)  : 연간 총 배정시간.
            - session_default_hours(int)  : 회기당 기본 근무시간.
            - carry_over_enabled   (bool) : 이월 적용 여부.
        total (int) : 전체 건수.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : VIEW_SENIOR 권한 없음
    """
    items = await business_unit_service.list_business_units(db, current_user.tenant_id, type, year)
    return {"items": items, "total": len(items)}


@router.post("/", response_model=BusinessUnitResponse, status_code=status.HTTP_201_CREATED)
async def create_business_unit(
    data: BusinessUnitCreate,
    request: Request,
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [사업단 생성] 새 사업단 등록. TENANT_ADMIN 전용.
    시장형은 근무시간 설정값(monthly_default_hours 등) 직접 입력 필수.
    공익활동형·사회서비스형은 규정에 따른 기본값 자동 적용.

    Args:
        data.name                 (str)          : 사업단명. 필수.
        data.type                 (str)          : 사업단 유형. 필수.
                                                   "public_benefit" | "social_service" | "market"
        data.year                 (int)          : 사업 연도. 필수.
        data.description          (str, optional): 설명.
        data.monthly_default_hours(int, optional): 월 기본 근무시간. 시장형 필수.
        data.monthly_max_hours    (int, optional): 월 최대 근무시간. 시장형 필수.
        data.total_annual_hours   (int, optional): 연간 총 배정시간. 시장형 필수.
        data.session_default_hours(int, optional): 회기당 기본 근무시간. 시장형 필수.
        data.session_max_hours    (int, optional): 회기당 최대 근무시간.
        data.carry_over_enabled   (bool,optional): 이월 적용 여부.

    Returns:
        BusinessUnitResponse : 생성된 사업단.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : TENANT_ADMIN 권한 없음
        422 : 시장형 필수 항목 누락
    """
    bu = await business_unit_service.create_business_unit(
        db, current_user.tenant_id, current_user.user_id, data
    )
    await db.commit()
    await db.refresh(bu)
    return bu


@router.put("/{bu_id}", response_model=BusinessUnitResponse)
async def update_business_unit(
    bu_id: uuid.UUID,
    data: BusinessUnitUpdate,
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [사업단 수정] 사업단 정보 부분 수정. TENANT_ADMIN 전용.
    시장형만 근무시간 설정값 수정 가능. 전달하지 않은 필드는 기존 값 유지.

    Args:
        bu_id                     (str, path)    : 수정할 사업단 UUID.
        data.name                 (str, optional): 변경할 사업단명.
        data.description          (str, optional): 변경할 설명.
        data.is_active            (bool,optional): 활성화 여부.
        data.monthly_default_hours(int, optional): 변경할 월 기본 근무시간 (시장형만).
        data.monthly_max_hours    (int, optional): 변경할 월 최대 근무시간 (시장형만).
        data.total_annual_hours   (int, optional): 변경할 연간 총 배정시간 (시장형만).
        data.session_default_hours(int, optional): 변경할 회기당 기본 근무시간 (시장형만).

    Returns:
        BusinessUnitResponse : 수정된 사업단.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : TENANT_ADMIN 권한 없음
        404 : 사업단 없음
    """
    bu = await business_unit_service.update_business_unit(
        db, str(bu_id), current_user.tenant_id, data
    )
    await db.commit()
    await db.refresh(bu)
    return bu


@router.delete("/{bu_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_unit(
    bu_id: uuid.UUID,
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [사업단 삭제] 사업단 삭제 처리. TENANT_ADMIN 전용.
    연결된 지출 내역이 있는 경우 삭제 불가 (400 반환).

    Args:
        bu_id (str, path) : 삭제할 사업단 UUID.

    Returns:
        없음 (HTTP 204 No Content)

    Raises:
        401 : 토큰 없음 또는 만료
        403 : TENANT_ADMIN 권한 없음
        404 : 사업단 없음
        400 : 연결된 지출 내역이 존재하여 삭제 불가
    """
    await business_unit_service.delete_business_unit(db, str(bu_id), current_user.tenant_id)
    await db.commit()

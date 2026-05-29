from __future__ import annotations
import uuid
from typing import Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, require_permission
from app.schemas.common import PaginatedResponse
from app.schemas.senior import SeniorCreate, SeniorResponse, SeniorUpdate
from app.services import senior_service

router = APIRouter(prefix="/seniors", tags=["seniors"])


@router.get("/", response_model=PaginatedResponse[SeniorResponse])
async def list_seniors(
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    business_unit_id: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    [어르신 목록] 사업단 필터 및 이름·근무장소 검색을 지원하는 어르신 목록 조회.
    어르신 관리·근무 입력·상담일지 페이지에서 공통 사용.

    Args:
        business_unit_id (str, optional) : 사업단 UUID. 전달 시 해당 사업단 소속만 조회.
        search           (str, optional) : 이름 또는 근무장소 검색어.

    Returns:
        items (List[SeniorResponse]) : 어르신 목록.
        total (int)                  : 전체 건수.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : VIEW_SENIOR 권한 없음
    """
    items = await senior_service.list_seniors(
        db, current_user.tenant_id, business_unit_id, search
    )
    return {"items": items, "total": len(items)}


@router.post("/", response_model=SeniorResponse, status_code=status.HTTP_201_CREATED)
async def create_senior(
    data: SeniorCreate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [어르신 등록] 새 어르신을 사업단에 등록. 감사 로그(IP 포함) 기록.

    Args:
        data.business_unit_id     (str)          : 배정할 사업단 UUID. 필수.
        data.name                 (str)          : 어르신 이름. 필수.
        data.birth_date           (str, date)    : 생년월일. 형식: "YYYY-MM-DD". 필수.
        data.workplace            (str, optional): 근무장소. 예) "강남구 보건소"
        data.hourly_wage          (int)          : 시급 (원). 필수. 예) 4000
        data.default_session_hours(int)          : 회기당 기본 근무시간. 기본값 3.
        data.notes                (str, optional): 특이사항 메모.

    Returns:
        SeniorResponse : 등록된 어르신 전체 정보 (id, allocated_hours 등 포함).

    Raises:
        401 : 토큰 없음 또는 만료
        403 : EDIT_SENIOR 권한 없음
        422 : 필수 항목 누락 또는 형식 오류
    """
    senior = await senior_service.create_senior(
        db, current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(senior)
    return senior


@router.get("/{senior_id}", response_model=SeniorResponse)
async def get_senior(
    senior_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [어르신 상세] 특정 어르신의 상세 정보 단건 조회.

    Args:
        senior_id (str, path) : 조회할 어르신 UUID.

    Returns:
        SeniorResponse : 어르신 상세 정보.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : VIEW_SENIOR 권한 없음
        404 : 해당 기관에 존재하지 않는 어르신
    """
    return await senior_service.get_senior(db, str(senior_id), current_user.tenant_id)


@router.put("/{senior_id}", response_model=SeniorResponse)
async def update_senior(
    senior_id: uuid.UUID,
    data: SeniorUpdate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [어르신 수정] 어르신 정보 부분 업데이트. 감사 로그(IP 포함) 기록.
    전달하지 않은 필드는 기존 값 유지 (PATCH 방식 동작).

    Args:
        senior_id                 (str, path)    : 수정할 어르신 UUID.
        data.name                 (str, optional): 변경할 이름.
        data.birth_date           (str, optional): 변경할 생년월일. 형식: "YYYY-MM-DD"
        data.workplace            (str, optional): 변경할 근무장소.
        data.hourly_wage          (int, optional): 변경할 시급 (원).
        data.default_session_hours(int, optional): 변경할 회기당 기본 근무시간.
        data.is_active            (bool,optional): 활성화 여부.
        data.notes                (str, optional): 변경할 메모.

    Returns:
        SeniorResponse : 수정된 어르신 전체 정보.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : EDIT_SENIOR 권한 없음
        404 : 해당 기관에 존재하지 않는 어르신
    """
    senior = await senior_service.update_senior(
        db, str(senior_id), current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(senior)
    return senior


@router.delete("/{senior_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_senior(
    senior_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("DELETE_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [어르신 삭제] 어르신 레코드 삭제 처리. 감사 로그(IP 포함) 기록.

    Args:
        senior_id (str, path) : 삭제할 어르신 UUID.

    Returns:
        없음 (HTTP 204 No Content)

    Raises:
        401 : 토큰 없음 또는 만료
        403 : DELETE_SENIOR 권한 없음
        404 : 해당 기관에 존재하지 않는 어르신
    """
    await senior_service.delete_senior(
        db, str(senior_id), current_user.tenant_id, current_user.user_id,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()

from __future__ import annotations
import uuid
from typing import Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, require_permission
from app.schemas.common import PaginatedResponse
from app.schemas.work_record import (
    MonthlyRowsResponse,
    WorkRecordCreate,
    WorkRecordReject,
    WorkRecordResponse,
    WorkRecordUpdate,
)
from app.services import work_record_service

router = APIRouter(prefix="/work-records", tags=["work-records"])


@router.get("/")
async def list_work_records(
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    senior_id: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    record_status: Optional[str] = None,
    business_unit_id: Optional[str] = None,
):
    """
    [근무기록 목록] 여러 조건으로 필터링한 근무기록 목록 조회.
    근무 입력 페이지(year+month+business_unit_id)와 결재 페이지(record_status=SUBMITTED)에서 공통 사용.

    Args:
        senior_id        (str, optional) : 특정 어르신 UUID로 필터.
        year             (int, optional) : 조회 연도.
        month            (int, optional) : 조회 월 (1~11).
        record_status    (str, optional) : 상태 필터.
                                           "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED"
        business_unit_id (str, optional) : 사업단 UUID로 필터.

    Returns:
        items (List[WorkRecordResponse]) : 근무기록 목록.
        total (int)                      : 전체 건수.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : VIEW_SENIOR 권한 없음
    """
    items = await work_record_service.list_work_records(
        db, current_user.tenant_id, senior_id, year, month, record_status, business_unit_id
    )
    return {"items": items, "total": len(items)}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_work_record(
    data: WorkRecordCreate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_WORK_RECORD"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [근무기록 생성] 어르신의 월 근무기록 신규 생성. 정책 위반 시 경고(warnings) 반환.
    감사 로그(IP 포함) 기록.

    Args:
        data.senior_id       (str)          : 어르신 UUID. 필수.
        data.year            (int)          : 근무 연도. 필수.
        data.month           (int)          : 근무 월. 필수. 범위: 1~11 (12월 입력 차단).
        data.worked_hours    (float)        : 월 총 근무시간. 필수. 최대 43.0시간.
                                              42.0 이상이면 overtime_reason 필수.
                                              43.0 초과 시 422 반환.
        data.worked_days     (int)          : 월 총 근무일수. 필수.
        data.amount_paid     (int)          : 지급 금액 (원). 필수.
        data.overtime_reason (str, optional): 초과근무 사유. worked_hours >= 42 이면 필수.

    Returns:
        data     (WorkRecordResponse) : 생성된 근무기록.
        warnings (List[str])         : 정책 위반 경고 메시지 목록 (초과근무 등).

    Raises:
        401 : 토큰 없음 또는 만료
        403 : EDIT_WORK_RECORD 권한 없음
        422 : month > 11, worked_hours > 43, 또는 필수 항목 누락
    """
    record, warnings = await work_record_service.create_work_record(
        db, current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(record)
    resp = WorkRecordResponse.model_validate(record)
    return {"data": resp, "warnings": warnings}


@router.put("/{record_id}")
async def update_work_record(
    record_id: uuid.UUID,
    data: WorkRecordUpdate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_WORK_RECORD"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [근무기록 수정] 기존 근무기록의 시간·금액·사유 수정. DRAFT 상태에서만 수정 가능.
    감사 로그(IP 포함) 기록.

    Args:
        record_id            (str, path)    : 수정할 근무기록 UUID.
        data.worked_hours    (float,optional): 변경할 월 총 근무시간. 최대 43.0시간.
        data.worked_days     (int,  optional): 변경할 월 총 근무일수.
        data.amount_paid     (int,  optional): 변경할 지급 금액 (원).
        data.overtime_reason (str,  optional): 변경할 초과근무 사유.

    Returns:
        data     (WorkRecordResponse) : 수정된 근무기록.
        warnings (List[str])         : 정책 위반 경고 메시지 목록.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : EDIT_WORK_RECORD 권한 없음
        404 : 근무기록 없음
        422 : worked_hours > 43
    """
    record, warnings = await work_record_service.update_work_record(
        db, str(record_id), current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(record)
    resp = WorkRecordResponse.model_validate(record)
    return {"data": resp, "warnings": warnings}


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_record(
    record_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_WORK_RECORD"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [근무기록 삭제] 근무기록 소프트 삭제 (deleted_at 기록). 감사 로그(IP 포함) 기록.

    Args:
        record_id (str, path) : 삭제할 근무기록 UUID.

    Returns:
        없음 (HTTP 204 No Content)

    Raises:
        401 : 토큰 없음 또는 만료
        403 : EDIT_WORK_RECORD 권한 없음
        404 : 근무기록 없음
    """
    await work_record_service.soft_delete_work_record(
        db, str(record_id), current_user.tenant_id, current_user.user_id,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()


@router.post("/{record_id}/submit", response_model=WorkRecordResponse)
async def submit_work_record(
    record_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_WORK_RECORD"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [결재 제출] 근무기록 상태를 DRAFT → SUBMITTED로 전환. 감사 로그(IP 포함) 기록.
    제출 후에는 수정 불가 (관리자가 반려해야 다시 DRAFT 상태로 전환됨).

    Args:
        record_id (str, path) : 제출할 근무기록 UUID.

    Returns:
        WorkRecordResponse : 상태가 SUBMITTED로 변경된 근무기록.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : EDIT_WORK_RECORD 권한 없음
        404 : 근무기록 없음
        400 : 이미 SUBMITTED 또는 APPROVED 상태인 경우
    """
    record = await work_record_service.submit_work_record(
        db, str(record_id), current_user.tenant_id, current_user.user_id,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(record)
    return record


@router.post("/{record_id}/approve", response_model=WorkRecordResponse)
async def approve_work_record(
    record_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("APPROVE_RECORD"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [결재 승인] 근무기록 상태를 SUBMITTED → APPROVED로 전환.
    APPROVE_RECORD 권한(TENANT_ADMIN) 필요. 감사 로그(IP 포함) 기록.
    승인 후 급여대장 출력 대상이 됨.

    Args:
        record_id (str, path) : 승인할 근무기록 UUID.

    Returns:
        WorkRecordResponse : 상태가 APPROVED로 변경된 근무기록 (approved_by, approved_at 포함).

    Raises:
        401 : 토큰 없음 또는 만료
        403 : APPROVE_RECORD 권한 없음
        404 : 근무기록 없음
        400 : SUBMITTED 상태가 아닌 경우
    """
    record = await work_record_service.approve_work_record(
        db, str(record_id), current_user.tenant_id, current_user.user_id,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(record)
    return record


@router.post("/{record_id}/reject", response_model=WorkRecordResponse)
async def reject_work_record(
    record_id: uuid.UUID,
    data: WorkRecordReject,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("APPROVE_RECORD"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [결재 반려] 근무기록 상태를 SUBMITTED → REJECTED로 전환. 반려 사유 필수 입력.
    APPROVE_RECORD 권한(TENANT_ADMIN) 필요. 감사 로그(IP 포함) 기록.
    반려된 기록은 담당자가 수정 후 재제출 가능.

    Args:
        record_id          (str, path) : 반려할 근무기록 UUID.
        data.reject_reason (str)       : 반려 사유. 필수. 예) "근무시간 오류, 재확인 필요"

    Returns:
        WorkRecordResponse : 상태가 REJECTED로 변경된 근무기록 (reject_reason 포함).

    Raises:
        401 : 토큰 없음 또는 만료
        403 : APPROVE_RECORD 권한 없음
        404 : 근무기록 없음
        400 : SUBMITTED 상태가 아닌 경우
        422 : reject_reason 누락
    """
    record = await work_record_service.reject_work_record(
        db, str(record_id), current_user.tenant_id, current_user.user_id,
        reject_reason=data.reject_reason,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/monthly-rows/{senior_id}/{year}/{month}", response_model=MonthlyRowsResponse)
async def get_monthly_rows(
    senior_id: uuid.UUID,
    year: int,
    month: int,
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [권장 근무 행 수] 어르신의 배정시간·사업단 설정·이월 적용 여부를 기반으로
    해당 월의 권장 근무 회기 수(행 수)를 계산해 반환.
    근무 입력 테이블의 행 수 자동 설정에 사용.

    Args:
        senior_id (str, path) : 어르신 UUID.
        year      (int, path) : 조회 연도.
        month     (int, path) : 조회 월 (1~11).

    Returns:
        senior_id        (str) : 어르신 UUID.
        year             (int) : 연도.
        month            (int) : 월.
        recommended_rows (int) : 권장 근무 행 수 (회기 수).

    Raises:
        401 : 토큰 없음 또는 만료
        403 : VIEW_SENIOR 권한 없음
        404 : 어르신 없음
    """
    from sqlalchemy import select
    from app.models.senior import Senior
    from app.models.business_unit import BusinessUnit
    from app.services.work_hours import calculate_monthly_rows

    senior_result = await db.execute(
        select(Senior).where(
            Senior.id == senior_id,
            Senior.tenant_id == uuid.UUID(current_user.tenant_id),
        )
    )
    senior = senior_result.scalar_one_or_none()
    if senior is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Senior not found")

    bu_result = await db.execute(
        select(BusinessUnit).where(BusinessUnit.id == senior.business_unit_id)
    )
    bu = bu_result.scalar_one_or_none()

    # work_hours.py는 sync Session을 사용 — 동기 DB 세션 별도 실행
    from app.core.database import get_sync_db
    with get_sync_db() as sync_db:
        rows = calculate_monthly_rows(
            db=sync_db,
            senior_id=str(senior_id),
            year=year,
            month=month,
            business_unit_type=bu.type.value,
            monthly_default_hours=bu.monthly_default_hours,
            monthly_max_hours=bu.monthly_max_hours,
            total_allocated_hours=senior.allocated_hours,
            session_hours=senior.default_session_hours,
            carry_over_enabled=bu.carry_over_enabled,
        )

    return MonthlyRowsResponse(
        senior_id=senior_id,
        year=year,
        month=month,
        recommended_rows=rows,
    )

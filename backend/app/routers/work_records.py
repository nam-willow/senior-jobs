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


@router.get("/", response_model=PaginatedResponse[WorkRecordResponse])
async def list_work_records(
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    senior_id: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    record_status: Optional[str] = None,
):
    items = await work_record_service.list_work_records(
        db, current_user.tenant_id, senior_id, year, month, record_status
    )
    return {"items": items, "total": len(items)}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_work_record(
    data: WorkRecordCreate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_WORK_RECORD"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
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

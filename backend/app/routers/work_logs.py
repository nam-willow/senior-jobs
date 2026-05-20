import uuid
from collections import defaultdict
from typing import Dict, List, Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_sync_db
from app.core.permissions import CurrentUser, require_permission
from app.core.tenant import get_tenant_db
from app.models.business_unit import BusinessUnit
from app.models.document_snapshot import DocumentSnapshot
from app.models.generated_file import GeneratedFile
from app.models.monthly_work_records import MonthlyWorkRecord, WorkRecordStatus
from app.models.senior import Senior
from app.services.work_hours import calculate_monthly_rows
from app.utils import excel_generator, pdf_generator
from app.tasks.export_tasks import export_work_logs_bulk
from app.utils.storage import build_path, get_storage, sha256_hex

router = APIRouter(prefix="/work-logs", tags=["work-logs"])


@router.get("/print-list/{year}/{month}")
async def get_print_list(
    year: int,
    month: int,
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    business_unit_id: Optional[str] = None,
):
    """
    이번달 어르신 전체 목록 + 행 수 케이스별 집계.
    응답: { seniors: [...], case_summary: {"10행": 45, "12행": 23}, total_pages: int }
    """
    q = (
        select(Senior, BusinessUnit)
        .join(BusinessUnit, Senior.business_unit_id == BusinessUnit.id)
        .where(Senior.tenant_id == uuid.UUID(current_user.tenant_id))
        .order_by(Senior.name)
    )
    if business_unit_id:
        q = q.where(Senior.business_unit_id == uuid.UUID(business_unit_id))

    result = await db.execute(q)
    rows = result.all()

    seniors_list = []
    case_counter: Dict[int, int] = defaultdict(int)

    with get_sync_db() as sync_db:
        for senior, bu in rows:
            try:
                row_count = calculate_monthly_rows(
                    db=sync_db,
                    senior_id=str(senior.id),
                    year=year,
                    month=month,
                    business_unit_type=bu.type.value,
                    monthly_default_hours=bu.monthly_default_hours,
                    monthly_max_hours=bu.monthly_max_hours,
                    total_allocated_hours=senior.allocated_hours,
                    session_hours=senior.default_session_hours,
                    carry_over_enabled=bu.carry_over_enabled,
                )
            except ValueError:
                row_count = 0

            case_counter[row_count] += 1
            seniors_list.append({
                "senior_id": str(senior.id),
                "name": senior.name,
                "workplace": senior.workplace or "",
                "row_count": row_count,
                "business_unit_name": bu.name,
            })

    case_summary = {f"{k}행": v for k, v in sorted(case_counter.items())}
    total_pages = sum(case_counter.values())

    return {
        "year": year,
        "month": month,
        "seniors": seniors_list,
        "case_summary": case_summary,
        "total_pages": total_pages,
    }


@router.get("/export/excel/{year}/{month}")
async def export_work_log_excel(
    year: int,
    month: int,
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    business_unit_id: Optional[str] = None,
):
    """근무일지 전체 어르신 Excel 단건 동기 다운로드. 어르신 1인 = 1시트."""
    q = (
        select(Senior, MonthlyWorkRecord)
        .outerjoin(
            MonthlyWorkRecord,
            (MonthlyWorkRecord.senior_id == Senior.id)
            & (MonthlyWorkRecord.year == year)
            & (MonthlyWorkRecord.month == month),
        )
        .where(Senior.tenant_id == uuid.UUID(current_user.tenant_id))
        .order_by(Senior.name)
    )
    if business_unit_id:
        q = q.where(Senior.business_unit_id == uuid.UUID(business_unit_id))

    result = await db.execute(q)
    rows = result.all()

    seniors_data = []
    for senior, record in rows:
        row_entries = []
        if record:
            for day in range(1, record.worked_days + 1):
                row_entries.append({"date": f"{year}/{month:02d}/{day:02d}", "hours": ""})
        seniors_data.append({
            "name": senior.name,
            "workplace": senior.workplace or "",
            "rows": row_entries,
        })

    file_bytes = excel_generator.generate_work_log_excel(year, month, seniors_data)
    filename = f"work_log_{year}_{month:02d}.xlsx"

    import io
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/export/bulk", status_code=status.HTTP_202_ACCEPTED)
async def export_work_log_bulk(
    year: int = Query(...),
    month: int = Query(...),
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))] = None,
    db: Annotated[AsyncSession, Depends(get_tenant_db)] = None,
    business_unit_id: Optional[str] = None,
):
    """근무일지 다건 비동기 내보내기. Celery task_id 반환."""
    task = export_work_logs_bulk.delay(
        year=year,
        month=month,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        business_unit_id=business_unit_id,
    )
    return {"task_id": task.id, "status": "PENDING"}


@router.get("/salary-statement/{year}/{month}")
async def get_salary_statement(
    year: int,
    month: int,
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    business_unit_id: Optional[str] = None,
    format: str = Query(default="excel", regex="^(excel|pdf)$"),
):
    """
    급여대장 출력 (APPROVED 상태 기준).
    format=excel → .xlsx 즉시 다운로드
    format=pdf   → .pdf 즉시 다운로드 + document_snapshots 자동 저장
    """
    q = (
        select(Senior, MonthlyWorkRecord, BusinessUnit)
        .join(MonthlyWorkRecord, MonthlyWorkRecord.senior_id == Senior.id)
        .join(BusinessUnit, Senior.business_unit_id == BusinessUnit.id)
        .where(
            Senior.tenant_id == uuid.UUID(current_user.tenant_id),
            MonthlyWorkRecord.year == year,
            MonthlyWorkRecord.month == month,
            MonthlyWorkRecord.status == WorkRecordStatus.APPROVED,
        )
        .order_by(Senior.name)
    )
    if business_unit_id:
        q = q.where(Senior.business_unit_id == uuid.UUID(business_unit_id))

    result = await db.execute(q)
    rows = result.all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="APPROVED 상태의 근무기록이 없습니다",
        )

    bu_name = rows[0][2].name if rows else ""
    records_data = [
        {
            "name": senior.name,
            "birth_date": str(senior.birth_date),
            "worked_hours": float(record.worked_hours),
            "amount_paid": int(record.amount_paid),
        }
        for senior, record, bu in rows
    ]

    if format == "pdf":
        file_bytes = pdf_generator.generate_salary_statement_pdf(year, month, bu_name, records_data)
        content_type = "application/pdf"
        ext = "pdf"
        filename = f"salary_{year}_{month:02d}.pdf"
    else:
        file_bytes = excel_generator.generate_salary_statement_excel(year, month, bu_name, records_data)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
        filename = f"salary_{year}_{month:02d}.xlsx"

    # document_snapshots 자동 저장
    for senior, record, bu in rows:
        snap = DocumentSnapshot(
            tenant_id=uuid.UUID(current_user.tenant_id),
            document_type="work_log",
            reference_id=record.id,
            snapshot_data={
                "year": year,
                "month": month,
                "senior_name": senior.name,
                "worked_hours": float(record.worked_hours),
                "amount_paid": int(record.amount_paid),
                "status": record.status.value,
            },
            created_by=uuid.UUID(current_user.user_id),
        )
        db.add(snap)

    # generated_files 저장 (MinIO 업로드)
    try:
        storage = get_storage()
        path = build_path(current_user.tenant_id, ext, filename)
        storage.upload(path, file_bytes, content_type)
        file_hash = sha256_hex(file_bytes)

        await db.flush()
        # 첫 번째 snap 참조로 생성 파일 기록
        gen = GeneratedFile(
            tenant_id=uuid.UUID(current_user.tenant_id),
            file_type=ext,
            file_path=path,
            file_hash=file_hash,
            created_by=uuid.UUID(current_user.user_id),
        )
        db.add(gen)
    except Exception:
        pass  # MinIO 실패해도 파일 반환은 진행

    await db.commit()

    import io
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

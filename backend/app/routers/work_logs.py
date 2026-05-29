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
    [근무일지 출력 목록] 해당 월 어르신 전체 목록 + 케이스별 행 수 집계 반환.
    근무일지 출력 페이지 진입 시 호출. 인쇄 매수 사전 확인 용도.

    Args:
        year             (int, path)      : 조회 연도.
        month            (int, path)      : 조회 월 (1~11).
        business_unit_id (str, optional)  : 사업단 UUID 필터. 생략 시 전체 사업단.

    Returns:
        year         (int)    : 조회 연도.
        month        (int)    : 조회 월.
        seniors      (List)   : 어르신 목록.
            - senior_id          (str) : 어르신 UUID.
            - name               (str) : 이름.
            - workplace          (str) : 근무장소.
            - row_count          (int) : 해당 월 권장 근무 행 수.
            - business_unit_name (str) : 소속 사업단명.
        case_summary (dict)   : 행 수별 어르신 수. 예) {"10행": 45, "12행": 23}
        total_pages  (int)    : 총 어르신 수 (인쇄 매수).

    Raises:
        401 : 토큰 없음 또는 만료
        403 : VIEW_SENIOR 권한 없음
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
    """
    [근무일지 Excel 다운로드] 해당 월 전체 어르신 근무일지를 Excel 파일로 즉시 다운로드.
    어르신 1인 = 1시트. 동기 처리. 대용량 시 bulk 엔드포인트 사용 권장.

    Args:
        year             (int, path)     : 다운로드 연도.
        month            (int, path)     : 다운로드 월 (1~11).
        business_unit_id (str, optional) : 사업단 UUID 필터. 생략 시 전체 사업단.

    Returns:
        파일 스트림 (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
        Content-Disposition: attachment; filename=work_log_{year}_{month:02d}.xlsx

    Raises:
        401 : 토큰 없음 또는 만료
        403 : VIEW_SENIOR 권한 없음
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

    seniors_data = []
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
            except (ValueError, Exception):
                row_count = 10

            seniors_data.append({
                "name": senior.name,
                "workplace": senior.workplace or "",
                "rows": [{"date": "", "hours": ""} for _ in range(row_count)],
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
    """
    [근무일지 대량 비동기 내보내기] Celery 태스크로 근무일지 대량 생성.
    즉시 task_id 반환 후 GET /tasks/{task_id}/status 로 완료 여부 폴링.
    어르신 수가 많거나 처리 시간이 긴 경우 이 엔드포인트 사용.

    Args:
        year             (int, query) : 내보내기 연도. 필수.
        month            (int, query) : 내보내기 월. 필수.
        business_unit_id (str, query) : 사업단 UUID 필터. 생략 시 전체.

    Returns:
        task_id (str) : Celery 태스크 ID. 상태 조회에 사용.
        status  (str) : 항상 "PENDING".

    Raises:
        401 : 토큰 없음 또는 만료
        403 : VIEW_SENIOR 권한 없음
    """
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
    [급여대장 다운로드] APPROVED 상태 근무기록 기준으로 급여대장 파일 생성 후 즉시 다운로드.
    PDF 선택 시 document_snapshots + generated_files 자동 저장. MinIO 업로드 실패해도 파일은 반환.
    APPROVED 기록이 없으면 404 반환.

    Args:
        year             (int, path)     : 급여대장 연도.
        month            (int, path)     : 급여대장 월.
        business_unit_id (str, optional) : 사업단 UUID 필터. 생략 시 전체 사업단.
        format           (str, query)    : 파일 형식. "excel" | "pdf". 기본값 "excel"

    Returns:
        format=excel → 파일 스트림 (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
                        filename: salary_{year}_{month:02d}.xlsx
        format=pdf   → 파일 스트림 (application/pdf)
                        filename: salary_{year}_{month:02d}.pdf

    Raises:
        401 : 토큰 없음 또는 만료
        403 : VIEW_SENIOR 권한 없음
        404 : 해당 월·사업단에 APPROVED 상태 근무기록 없음
        422 : format이 "excel" 또는 "pdf"가 아닌 경우
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

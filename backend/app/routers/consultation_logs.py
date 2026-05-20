import io
import uuid
from typing import List, Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, require_permission
from app.models.consultation_log import ConsultationLog
from app.models.document_snapshot import DocumentSnapshot
from app.models.generated_file import GeneratedFile
from app.models.senior import Senior
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.consultation_log import (
    ConsultationLogCreate,
    ConsultationLogResponse,
    ConsultationLogUpdate,
)
from app.services import consultation_log_service
from app.tasks.export_tasks import export_consultation_logs_bulk as _bulk_task
from app.utils import excel_generator, pdf_generator
from app.utils.storage import build_path, get_storage, sha256_hex

router = APIRouter(prefix="/consultation-logs", tags=["consultation-logs"])


@router.get("/", response_model=PaginatedResponse[ConsultationLogResponse])
async def list_consultation_logs(
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    senior_id: Optional[str] = None,
):
    items = await consultation_log_service.list_consultation_logs(
        db, current_user.tenant_id, senior_id
    )
    return {"items": items, "total": len(items)}


@router.post("/", response_model=ConsultationLogResponse, status_code=status.HTTP_201_CREATED)
async def create_consultation_log(
    data: ConsultationLogCreate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    log = await consultation_log_service.create_consultation_log(
        db, current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(log)
    return log


@router.put("/{log_id}", response_model=ConsultationLogResponse)
async def update_consultation_log(
    log_id: uuid.UUID,
    data: ConsultationLogUpdate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    log = await consultation_log_service.update_consultation_log(
        db, str(log_id), current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(log)
    return log


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_consultation_log(
    log_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    await consultation_log_service.delete_consultation_log(
        db, str(log_id), current_user.tenant_id, current_user.user_id,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()


# ── Export 엔드포인트 ──────────────────────────────────────────────────────────

async def _fetch_log_with_context(db: AsyncSession, log_id: uuid.UUID, tenant_id: str):
    """상담일지 단건 + senior + social_worker 조회."""
    result = await db.execute(
        select(ConsultationLog, Senior, User)
        .join(Senior, ConsultationLog.senior_id == Senior.id)
        .join(User, ConsultationLog.social_worker_id == User.id)
        .where(
            ConsultationLog.id == log_id,
            ConsultationLog.tenant_id == uuid.UUID(tenant_id),
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation log not found")
    return row


async def _save_snapshot_and_file(
    db: AsyncSession,
    log: ConsultationLog,
    tenant_id: str,
    user_id: str,
    file_bytes: bytes,
    file_type: str,
    file_path: str,
) -> None:
    snap = DocumentSnapshot(
        tenant_id=uuid.UUID(tenant_id),
        document_type="consultation_log",
        reference_id=log.id,
        snapshot_data={
            "consultation_date": str(log.consultation_date),
            "method": log.method.value,
            "content": log.content,
            "senior_id": str(log.senior_id),
        },
        created_by=uuid.UUID(user_id),
    )
    db.add(snap)
    await db.flush()

    gen = GeneratedFile(
        tenant_id=uuid.UUID(tenant_id),
        file_type=file_type,
        file_path=file_path,
        file_hash=sha256_hex(file_bytes),
        document_snapshot_id=snap.id,
        created_by=uuid.UUID(user_id),
    )
    db.add(gen)


@router.get("/export/excel/{log_id}")
async def export_consultation_log_excel(
    log_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """상담일지 단건 Excel 동기 다운로드 + document_snapshots 저장."""
    log, senior, worker = await _fetch_log_with_context(db, log_id, current_user.tenant_id)

    log_data = [{
        "consultation_date": str(log.consultation_date),
        "method": log.method.value,
        "content": log.content,
        "memo": log.memo or "",
        "social_worker_name": worker.name,
        "default_session_hours": log.default_session_hours,
    }]

    file_bytes = excel_generator.generate_consultation_log_excel(log_data, senior_name=senior.name)
    filename = f"consultation_{log_id}.xlsx"
    path = build_path(current_user.tenant_id, "excel", filename)

    try:
        storage = get_storage()
        storage.upload(path, file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        await _save_snapshot_and_file(db, log, current_user.tenant_id, current_user.user_id, file_bytes, "xlsx", path)
    except Exception:
        pass

    await db.commit()

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/pdf/{log_id}")
async def export_consultation_log_pdf(
    log_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """상담일지 단건 PDF 동기 다운로드 + document_snapshots 저장."""
    log, senior, worker = await _fetch_log_with_context(db, log_id, current_user.tenant_id)

    log_data = [{
        "consultation_date": str(log.consultation_date),
        "method": log.method.value,
        "content": log.content,
        "memo": log.memo or "",
        "social_worker_name": worker.name,
        "default_session_hours": log.default_session_hours,
    }]

    file_bytes = pdf_generator.generate_consultation_log_pdf(log_data, senior_name=senior.name)
    filename = f"consultation_{log_id}.pdf"
    path = build_path(current_user.tenant_id, "pdf", filename)

    try:
        storage = get_storage()
        storage.upload(path, file_bytes, "application/pdf")
        await _save_snapshot_and_file(db, log, current_user.tenant_id, current_user.user_id, file_bytes, "pdf", path)
    except Exception:
        pass

    await db.commit()

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/export/bulk", status_code=status.HTTP_202_ACCEPTED)
async def export_consultation_logs_bulk(
    log_ids: List[str],
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    format: str = Query(default="excel", regex="^(excel|pdf)$"),
):
    """상담일지 다건 비동기 내보내기. Celery task_id 반환."""
    task = _bulk_task.delay(
        log_ids=log_ids,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        format=format,
    )
    return {"task_id": task.id, "status": "PENDING"}

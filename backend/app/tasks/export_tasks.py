"""
Celery 비동기 내보내기 태스크.

태스크 결과 구조:
  성공: {"status": "SUCCESS", "url": presigned_url, "filename": str}
  실패: {"status": "FAILURE", "error": str}

동기 SQLAlchemy(psycopg2) 사용 — Celery 워커는 이벤트 루프 없음.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select, text

from app.core.database import get_sync_db
from app.models.consultation_log import ConsultationLog
from app.models.document_snapshot import DocumentSnapshot
from app.models.generated_file import GeneratedFile
from app.models.monthly_work_records import MonthlyWorkRecord, WorkRecordStatus
from app.models.senior import Senior
from app.models.user import User
from app.tasks.celery_app import celery_app
from app.utils import excel_generator, pdf_generator
from app.utils.storage import build_path, get_storage, sha256_hex


def _set_tenant(db, tenant_id: str) -> None:
    db.execute(text(f"SET app.current_tenant = '{tenant_id}'"))


# ── 상담일지 다건 내보내기 ────────────────────────────────────────────────────

@celery_app.task(bind=True, name="export_consultation_logs_bulk")
def export_consultation_logs_bulk(
    self,
    log_ids: List[str],
    tenant_id: str,
    user_id: str,
    format: str = "excel",  # "excel" | "pdf"
) -> Dict:
    try:
        with get_sync_db() as db:
            _set_tenant(db, tenant_id)

            logs_result = db.execute(
                select(ConsultationLog, Senior, User)
                .join(Senior, ConsultationLog.senior_id == Senior.id)
                .join(User, ConsultationLog.social_worker_id == User.id)
                .where(
                    ConsultationLog.id.in_([uuid.UUID(i) for i in log_ids]),
                    ConsultationLog.tenant_id == uuid.UUID(tenant_id),
                )
                .order_by(ConsultationLog.consultation_date)
            )
            rows = logs_result.all()

            log_data = [
                {
                    "consultation_date": str(log.consultation_date),
                    "method": log.method.value,
                    "content": log.content,
                    "memo": log.memo or "",
                    "social_worker_name": worker.name,
                    "default_session_hours": log.default_session_hours,
                }
                for log, senior, worker in rows
            ]

            if format == "pdf":
                file_bytes = pdf_generator.generate_consultation_log_pdf(log_data)
                content_type = "application/pdf"
                ext = "pdf"
                file_subdir = "pdf"
            else:
                file_bytes = excel_generator.generate_consultation_log_excel(log_data)
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ext = "xlsx"
                file_subdir = "excel"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"consultation_logs_{timestamp}.{ext}"
            path = build_path(tenant_id, file_subdir, filename)
            storage = get_storage()
            storage.upload(path, file_bytes, content_type)
            url = storage.get_presigned_url(path)
            file_hash = sha256_hex(file_bytes)

            # document_snapshots + generated_files 저장
            for log, senior, worker in rows:
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
                db.flush()

                gen_file = GeneratedFile(
                    tenant_id=uuid.UUID(tenant_id),
                    file_type=ext,
                    file_path=path,
                    file_hash=file_hash,
                    document_snapshot_id=snap.id,
                    created_by=uuid.UUID(user_id),
                )
                db.add(gen_file)

            db.commit()

        return {"status": "SUCCESS", "url": url, "filename": filename}

    except Exception as exc:
        return {"status": "FAILURE", "error": str(exc)}


# ── 근무일지 다건 내보내기 ────────────────────────────────────────────────────

@celery_app.task(bind=True, name="export_work_logs_bulk")
def export_work_logs_bulk(
    self,
    year: int,
    month: int,
    tenant_id: str,
    user_id: str,
    business_unit_id: Optional[str] = None,
) -> Dict:
    try:
        with get_sync_db() as db:
            _set_tenant(db, tenant_id)

            q = (
                select(Senior, MonthlyWorkRecord)
                .join(MonthlyWorkRecord, MonthlyWorkRecord.senior_id == Senior.id, isouter=True)
                .where(
                    Senior.tenant_id == uuid.UUID(tenant_id),
                    MonthlyWorkRecord.year == year,
                    MonthlyWorkRecord.month == month,
                )
                .order_by(Senior.name)
            )
            if business_unit_id:
                q = q.where(Senior.business_unit_id == uuid.UUID(business_unit_id))

            rows = db.execute(q).all()

            seniors_data = []
            for senior, record in rows:
                rows_data = []
                if record:
                    for day in range(1, record.worked_days + 1):
                        rows_data.append({"date": f"{year}/{month:02d}/{day:02d}", "hours": ""})
                seniors_data.append({
                    "name": senior.name,
                    "workplace": senior.workplace or "",
                    "rows": rows_data,
                })

            file_bytes = excel_generator.generate_work_log_excel(year, month, seniors_data)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"work_logs_{year}_{month:02d}_{timestamp}.xlsx"
            path = build_path(tenant_id, "excel", filename)
            storage = get_storage()
            storage.upload(path, file_bytes, content_type)
            url = storage.get_presigned_url(path)

            db.commit()

        return {"status": "SUCCESS", "url": url, "filename": filename}

    except Exception as exc:
        return {"status": "FAILURE", "error": str(exc)}

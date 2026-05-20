"""
OR-* 출력 라우터 단위 테스트.
work_logs, tasks 라우터 happy-path (mock 기반).
"""
from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_db, get_redis
from app.core.tenant import get_tenant_db
from app.core.permissions import get_current_user, CurrentUser
from app.models.monthly_work_records import WorkRecordStatus

TENANT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
BU_ID = str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


FAKE_USER = CurrentUser(
    user_id=USER_ID,
    tenant_id=TENANT_ID,
    role="platform_admin",
    jti="test-jti",
)


def make_mock_db(all_rows=None, scalar_return=None):
    mock_db = AsyncMock()
    result = MagicMock()
    result.all.return_value = all_rows or []
    result.scalars.return_value.all.return_value = []
    result.scalar_one_or_none.return_value = scalar_return
    mock_db.execute.return_value = result
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    return mock_db


class _Client:
    def __init__(self, mock_db):
        self._mock_db = mock_db

    async def __aenter__(self):
        async def _override_db() -> AsyncGenerator:
            yield self._mock_db

        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_tenant_db] = _override_db
        app.dependency_overrides[get_redis] = lambda: AsyncMock()
        transport = ASGITransport(app=app)
        self._inner = AsyncClient(transport=transport, base_url="http://test")
        return await self._inner.__aenter__()

    async def __aexit__(self, *args):
        app.dependency_overrides.clear()
        return await self._inner.__aexit__(*args)


def fake_senior():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        business_unit_id=uuid.UUID(BU_ID),
        name="홍길동",
        birth_date=date(1950, 1, 1),
        workplace="테스트직장",
        allocated_hours=330,
        hourly_wage=12000,
        default_session_hours=3,
        is_active=True,
        notes=None,
        created_by=uuid.UUID(USER_ID),
        created_at=_now(),
        deleted_at=None,
    )


def fake_bu():
    return SimpleNamespace(
        id=uuid.UUID(BU_ID),
        tenant_id=uuid.UUID(TENANT_ID),
        name="공익활동 1단",
        type=SimpleNamespace(value="public_benefit"),
        monthly_default_hours=30,
        monthly_max_hours=42,
        total_annual_hours=330,
        session_default_hours=3,
        session_max_hours=4,
        carry_over_enabled=True,
        is_active=True,
    )


def fake_work_record(status=WorkRecordStatus.APPROVED):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        senior_id=uuid.uuid4(),
        year=2026,
        month=5,
        worked_hours=Decimal("30.0"),
        worked_days=10,
        amount_paid=360000,
        status=status,
        approved_by=None,
        approved_at=None,
        reject_reason=None,
        overtime_reason=None,
        created_by=uuid.UUID(USER_ID),
        created_at=_now(),
        deleted_at=None,
    )


# ── OR-01~05: /work-logs 라우터 ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_OR01_print_list_ok():
    """OR-01: GET /work-logs/print-list/{year}/{month} — 200 응답."""
    senior = fake_senior()
    bu = fake_bu()

    mock_db = make_mock_db(all_rows=[(senior, bu)])

    with patch("app.routers.work_logs.get_sync_db") as mock_sync:
        sync_db = MagicMock()
        mock_sync.return_value.__enter__ = MagicMock(return_value=sync_db)
        mock_sync.return_value.__exit__ = MagicMock(return_value=False)
        with patch("app.routers.work_logs.calculate_monthly_rows", return_value=10):
            async with _Client(mock_db) as client:
                r = await client.get("/api/v1/work-logs/print-list/2026/5")
    assert r.status_code == 200
    body = r.json()
    assert "seniors" in body
    assert "case_summary" in body
    assert body["year"] == 2026
    assert body["month"] == 5


@pytest.mark.asyncio
async def test_OR02_print_list_empty():
    """OR-02: 어르신 없으면 seniors=[], total_pages=0."""
    mock_db = make_mock_db(all_rows=[])

    with patch("app.routers.work_logs.get_sync_db") as mock_sync:
        mock_sync.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_sync.return_value.__exit__ = MagicMock(return_value=False)
        async with _Client(mock_db) as client:
            r = await client.get("/api/v1/work-logs/print-list/2026/5")
    assert r.status_code == 200
    assert r.json()["seniors"] == []
    assert r.json()["total_pages"] == 0


@pytest.mark.asyncio
async def test_OR03_export_excel_ok():
    """OR-03: GET /work-logs/export/excel/{year}/{month} — 200 + xlsx."""
    senior = fake_senior()
    record = fake_work_record()

    mock_db = make_mock_db(all_rows=[(senior, record)])

    async with _Client(mock_db) as client:
        r = await client.get("/api/v1/work-logs/export/excel/2026/5")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]


@pytest.mark.asyncio
async def test_OR04_bulk_export_returns_task_id():
    """OR-04: POST /work-logs/export/bulk — 202 + task_id."""
    mock_db = make_mock_db()

    with patch("app.routers.work_logs.export_work_logs_bulk") as mock_task:
        mock_task.delay.return_value.id = "fake-task-id"
        async with _Client(mock_db) as client:
            r = await client.post("/api/v1/work-logs/export/bulk?year=2026&month=5")
    assert r.status_code == 202
    assert r.json()["task_id"] == "fake-task-id"
    assert r.json()["status"] == "PENDING"


@pytest.mark.asyncio
async def test_OR05_salary_statement_404_when_no_approved():
    """OR-05: 급여대장 — APPROVED 없으면 404."""
    mock_db = make_mock_db(all_rows=[])  # 빈 결과

    async with _Client(mock_db) as client:
        r = await client.get("/api/v1/work-logs/salary-statement/2026/5")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_OR06_salary_statement_excel_ok():
    """OR-06: 급여대장 Excel 다운로드 — 200 + xlsx."""
    senior = fake_senior()
    record = fake_work_record(WorkRecordStatus.APPROVED)
    bu = fake_bu()

    mock_db = make_mock_db(all_rows=[(senior, record, bu)])

    with patch("app.routers.work_logs.get_storage") as mock_storage:
        mock_storage.return_value.upload = MagicMock()
        async with _Client(mock_db) as client:
            r = await client.get("/api/v1/work-logs/salary-statement/2026/5?format=excel")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]


@pytest.mark.asyncio
async def test_OR07_salary_statement_pdf_ok():
    """OR-07: 급여대장 PDF 다운로드 — 200 + pdf."""
    senior = fake_senior()
    record = fake_work_record(WorkRecordStatus.APPROVED)
    bu = fake_bu()

    mock_db = make_mock_db(all_rows=[(senior, record, bu)])

    with patch("app.routers.work_logs.get_storage") as mock_storage:
        mock_storage.return_value.upload = MagicMock()
        async with _Client(mock_db) as client:
            r = await client.get("/api/v1/work-logs/salary-statement/2026/5?format=pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


# ── OR-08~11: /tasks 라우터 ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_OR08_task_status_pending():
    """OR-08: GET /tasks/{id}/status — PENDING 상태."""
    mock_db = make_mock_db()
    task_id = str(uuid.uuid4())

    with patch("app.routers.tasks.AsyncResult") as MockResult:
        MockResult.return_value.state = "PENDING"
        async with _Client(mock_db) as client:
            r = await client.get(f"/api/v1/tasks/{task_id}/status")
    assert r.status_code == 200
    assert r.json()["status"] == "PENDING"


@pytest.mark.asyncio
async def test_OR09_task_status_success():
    """OR-09: GET /tasks/{id}/status — SUCCESS + result."""
    mock_db = make_mock_db()
    task_id = str(uuid.uuid4())
    url = "http://minio/presigned/file.xlsx"

    with patch("app.routers.tasks.AsyncResult") as MockResult:
        MockResult.return_value.state = "SUCCESS"
        MockResult.return_value.result = {"status": "SUCCESS", "url": url, "filename": "file.xlsx"}
        async with _Client(mock_db) as client:
            r = await client.get(f"/api/v1/tasks/{task_id}/status")
    body = r.json()
    assert body["status"] == "SUCCESS"
    assert body["result"]["url"] == url


@pytest.mark.asyncio
async def test_OR10_task_status_failure():
    """OR-10: GET /tasks/{id}/status — FAILURE."""
    mock_db = make_mock_db()
    task_id = str(uuid.uuid4())

    with patch("app.routers.tasks.AsyncResult") as MockResult:
        MockResult.return_value.state = "FAILURE"
        MockResult.return_value.result = Exception("DB 오류")
        async with _Client(mock_db) as client:
            r = await client.get(f"/api/v1/tasks/{task_id}/status")
    assert r.status_code == 200
    assert r.json()["status"] == "FAILURE"


@pytest.mark.asyncio
async def test_OR11_task_inner_failure():
    """OR-11: SUCCESS 상태지만 task result가 FAILURE인 경우."""
    mock_db = make_mock_db()
    task_id = str(uuid.uuid4())

    with patch("app.routers.tasks.AsyncResult") as MockResult:
        MockResult.return_value.state = "SUCCESS"
        MockResult.return_value.result = {"status": "FAILURE", "error": "MinIO 연결 실패"}
        async with _Client(mock_db) as client:
            r = await client.get(f"/api/v1/tasks/{task_id}/status")
    body = r.json()
    assert body["status"] == "FAILURE"


# ── OR-12~14: /consultation-logs export 라우터 ────────────────────────────────

@pytest.mark.asyncio
async def test_OR12_consultation_export_excel():
    """OR-12: GET /consultation-logs/export/excel/{id} — 200 + xlsx."""
    log_id = uuid.uuid4()

    log = SimpleNamespace(
        id=log_id,
        tenant_id=uuid.UUID(TENANT_ID),
        senior_id=uuid.uuid4(),
        social_worker_id=uuid.UUID(USER_ID),
        consultation_date=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        method=SimpleNamespace(value="phone"),
        content="상담 내용",
        memo="",
        default_session_hours=3,
        deleted_at=None,
    )
    senior = SimpleNamespace(id=uuid.uuid4(), name="김노인", deleted_at=None)
    worker = SimpleNamespace(id=uuid.UUID(USER_ID), name="홍복지사", deleted_at=None)

    mock_db = make_mock_db()
    mock_db.execute.return_value.one_or_none.return_value = (log, senior, worker)

    with patch("app.routers.consultation_logs.get_storage") as ms:
        ms.return_value.upload = MagicMock()
        async with _Client(mock_db) as client:
            r = await client.get(f"/api/v1/consultation-logs/export/excel/{log_id}")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]


@pytest.mark.asyncio
async def test_OR13_consultation_export_pdf():
    """OR-13: GET /consultation-logs/export/pdf/{id} — 200 + pdf."""
    log_id = uuid.uuid4()

    log = SimpleNamespace(
        id=log_id,
        tenant_id=uuid.UUID(TENANT_ID),
        senior_id=uuid.uuid4(),
        social_worker_id=uuid.UUID(USER_ID),
        consultation_date=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        method=SimpleNamespace(value="visit"),
        content="방문 상담",
        memo=None,
        default_session_hours=3,
        deleted_at=None,
    )
    senior = SimpleNamespace(id=uuid.uuid4(), name="이노인", deleted_at=None)
    worker = SimpleNamespace(id=uuid.UUID(USER_ID), name="홍복지사", deleted_at=None)

    mock_db = make_mock_db()
    mock_db.execute.return_value.one_or_none.return_value = (log, senior, worker)

    with patch("app.routers.consultation_logs.get_storage") as ms:
        ms.return_value.upload = MagicMock()
        async with _Client(mock_db) as client:
            r = await client.get(f"/api/v1/consultation-logs/export/pdf/{log_id}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_OR14_consultation_export_bulk_202():
    """OR-14: POST /consultation-logs/export/bulk — 202 + task_id."""
    mock_db = make_mock_db()
    log_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    with patch("app.routers.consultation_logs._bulk_task") as mock_task:
        mock_task.delay.return_value.id = "bulk-task-id"
        async with _Client(mock_db) as client:
            r = await client.post(
                "/api/v1/consultation-logs/export/bulk?format=excel",
                json=log_ids,
            )
    assert r.status_code == 202
    assert r.json()["task_id"] == "bulk-task-id"

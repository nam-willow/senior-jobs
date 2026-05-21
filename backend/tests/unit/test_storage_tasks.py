"""
storage.py 및 export_tasks.py 단위 테스트
"""
import uuid
from unittest.mock import MagicMock, patch, call
import pytest

from app.utils.storage import sha256_hex, build_path, get_storage, MinIOStorage


# ── storage.py ────────────────────────────────────────────────────────────────

def test_sha256_hex_deterministic():
    data = b"hello world"
    result = sha256_hex(data)
    assert len(result) == 64
    assert result == sha256_hex(data)


def test_sha256_hex_empty():
    result = sha256_hex(b"")
    assert len(result) == 64
    assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_build_path_format():
    tid = str(uuid.uuid4())
    path = build_path(tid, "pdf", "test.pdf")
    assert path == f"{tid}/pdf/test.pdf"


def test_build_path_excel():
    tid = "abc-123"
    path = build_path(tid, "excel", "work_log.xlsx")
    assert path == "abc-123/excel/work_log.xlsx"


@patch("app.utils.storage.Minio")
def test_minio_storage_upload(mock_minio_cls):
    mock_client = MagicMock()
    mock_minio_cls.return_value = mock_client
    mock_client.bucket_exists.return_value = True

    storage = MinIOStorage()
    storage.upload("tenant/pdf/test.pdf", b"data", "application/pdf")

    mock_client.put_object.assert_called_once()
    call_args = mock_client.put_object.call_args
    assert call_args.kwargs["object_name"] == "tenant/pdf/test.pdf"
    assert call_args.kwargs["content_type"] == "application/pdf"


@patch("app.utils.storage.Minio")
def test_minio_storage_download(mock_minio_cls):
    mock_client = MagicMock()
    mock_minio_cls.return_value = mock_client
    mock_client.bucket_exists.return_value = True

    mock_response = MagicMock()
    mock_response.read.return_value = b"file content"
    mock_client.get_object.return_value = mock_response

    storage = MinIOStorage()
    result = storage.download("tenant/pdf/test.pdf")

    assert result == b"file content"
    mock_response.close.assert_called_once()
    mock_response.release_conn.assert_called_once()


@patch("app.utils.storage.Minio")
def test_minio_storage_presigned_url(mock_minio_cls):
    mock_client = MagicMock()
    mock_minio_cls.return_value = mock_client
    mock_client.bucket_exists.return_value = True
    mock_client.presigned_get_object.return_value = "https://minio.example.com/file?sig=xyz"

    storage = MinIOStorage()
    url = storage.get_presigned_url("tenant/pdf/test.pdf", expires=1800)

    assert url == "https://minio.example.com/file?sig=xyz"
    mock_client.presigned_get_object.assert_called_once()


@patch("app.utils.storage.Minio")
def test_minio_storage_delete(mock_minio_cls):
    mock_client = MagicMock()
    mock_minio_cls.return_value = mock_client
    mock_client.bucket_exists.return_value = True

    storage = MinIOStorage()
    storage.delete("tenant/pdf/test.pdf")

    mock_client.remove_object.assert_called_once_with("senior-jobs", "tenant/pdf/test.pdf")


@patch("app.utils.storage.Minio")
def test_minio_ensure_bucket_creates_if_missing(mock_minio_cls):
    mock_client = MagicMock()
    mock_minio_cls.return_value = mock_client
    mock_client.bucket_exists.return_value = False

    MinIOStorage()

    mock_client.make_bucket.assert_called_once()


@patch("app.utils.storage._storage", None)
@patch("app.utils.storage.Minio")
def test_get_storage_singleton(mock_minio_cls):
    mock_client = MagicMock()
    mock_minio_cls.return_value = mock_client
    mock_client.bucket_exists.return_value = True

    s1 = get_storage()
    s2 = get_storage()
    assert s1 is s2


# ── export_tasks.py (Celery task 단위 mock 테스트) ────────────────────────────

def test_export_tasks_module_importable():
    from app.tasks import export_tasks
    assert hasattr(export_tasks, "export_consultation_logs_bulk")
    assert hasattr(export_tasks, "export_work_logs_bulk")


def test_export_consultation_logs_bulk_task_name():
    from app.tasks.export_tasks import export_consultation_logs_bulk
    assert export_consultation_logs_bulk.name == "export_consultation_logs_bulk"


def test_export_work_logs_bulk_task_name():
    from app.tasks.export_tasks import export_work_logs_bulk
    assert export_work_logs_bulk.name == "export_work_logs_bulk"


@patch("app.tasks.export_tasks.get_sync_db")
def test_export_consultation_logs_bulk_db_error_returns_failure(mock_get_db):
    from app.tasks.export_tasks import export_consultation_logs_bulk

    mock_db_ctx = MagicMock()
    mock_db_ctx.__enter__ = MagicMock(side_effect=Exception("DB connection failed"))
    mock_db_ctx.__exit__ = MagicMock(return_value=False)
    mock_get_db.return_value = mock_db_ctx

    result = export_consultation_logs_bulk.run(
        log_ids=["fake-id"],
        tenant_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        format="excel",
    )

    assert result["status"] == "FAILURE"
    assert "error" in result


@patch("app.tasks.export_tasks.get_sync_db")
def test_export_work_logs_bulk_db_error_returns_failure(mock_get_db):
    from app.tasks.export_tasks import export_work_logs_bulk

    mock_db_ctx = MagicMock()
    mock_db_ctx.__enter__ = MagicMock(side_effect=Exception("DB connection failed"))
    mock_db_ctx.__exit__ = MagicMock(return_value=False)
    mock_get_db.return_value = mock_db_ctx

    result = export_work_logs_bulk.run(
        year=2026, month=5,
        tenant_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
    )

    assert result["status"] == "FAILURE"
    assert "error" in result

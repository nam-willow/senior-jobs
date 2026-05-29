from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from celery.result import AsyncResult

from app.core.permissions import CurrentUser, require_permission
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}/status")
async def get_task_status(
    task_id: str,
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
):
    """
    [태스크 상태 조회] Celery 비동기 태스크의 현재 진행 상태 조회.
    bulk export 요청 후 task_id로 완료 여부를 폴링할 때 사용.

    Args:
        task_id (str, path) : 조회할 Celery 태스크 ID.
                              bulk export 엔드포인트가 반환한 task_id를 사용.

    Returns:
        task_id (str)      : 조회한 태스크 ID.
        status  (str)      : 태스크 상태.
                             "PENDING"  — 대기 중 (아직 시작 전).
                             "STARTED"  — 처리 중.
                             "SUCCESS"  — 완료.
                             "FAILURE"  — 실패.
        result  (obj|null) : SUCCESS 시 태스크 결과 데이터. 그 외 null.
                             FAILURE 시 {"error": "에러 메시지"}.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : VIEW_SENIOR 권한 없음
    """
    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        return {"task_id": task_id, "status": "PENDING", "result": None}

    if result.state == "STARTED":
        return {"task_id": task_id, "status": "STARTED", "result": None}

    if result.state == "SUCCESS":
        task_result = result.result
        if isinstance(task_result, dict) and task_result.get("status") == "FAILURE":
            return {"task_id": task_id, "status": "FAILURE", "result": task_result}
        return {"task_id": task_id, "status": "SUCCESS", "result": task_result}

    if result.state == "FAILURE":
        return {
            "task_id": task_id,
            "status": "FAILURE",
            "result": {"error": str(result.result)},
        }

    return {"task_id": task_id, "status": result.state, "result": None}

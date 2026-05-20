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
    """Celery 태스크 진행 상태 조회."""
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

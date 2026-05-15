"""
structlog 기반 구조화 JSON 로깅.
모든 로그에 trace_id(X-Request-ID), tenant_id, user_id 자동 바인딩.
"""
import logging
import sys
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

_REQUEST_ID_HEADER = "X-Request-ID"


def setup_logging() -> None:
    log_level = logging.DEBUG if settings.debug else logging.INFO

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # uvicorn / sqlalchemy 로거도 structlog 수준에 맞게 조정
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(log_level)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    return structlog.get_logger(name)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    - X-Request-ID 없으면 UUID 자동 생성 후 응답 헤더에도 포함
    - 요청/응답 구조화 로그 기록
    - structlog contextvars에 trace_id 바인딩 (이후 로그에 자동 포함)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get(_REQUEST_ID_HEADER) or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        logger = get_logger("http")
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=_get_client_ip(request),
        )

        response: Response = await call_next(request)
        response.headers[_REQUEST_ID_HEADER] = trace_id

        logger.info(
            "request_finished",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
        return response


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

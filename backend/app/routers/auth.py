from typing_extensions import Annotated

import uuid
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis
from app.core.permissions import CurrentUser, get_current_user
from app.core.tenant import get_tenant_db
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """
    [로그인] 이메일 + 비밀번호 인증 후 access_token / refresh_token 발급.
    Rate limit: 10회/분. 로그인 성공·실패 모두 감사 로그(IP 포함) 기록.

    Args:
        body.email    (str) : 로그인 이메일. 소문자 자동 변환. 예) "admin@example.com"
        body.password (str) : 비밀번호 평문. 서비스 내부에서 bcrypt 해시 비교.

    Returns:
        access_token  (str) : JWT. 만료 60분. 요청 시 Authorization: Bearer {token} 헤더에 사용.
        refresh_token (str) : 재발급용 토큰. 만료 7일. Redis에 저장됨.
        token_type    (str) : 항상 "bearer".

    Raises:
        401 : 이메일 없음 또는 비밀번호 불일치
        429 : Rate limit 초과 (10회/분)
    """
    return await auth_service.login(
        db=db,
        redis=redis,
        email=body.email,
        password=body.password,
        ip_address=_get_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """
    [토큰 갱신] 유효한 refresh_token으로 새 access_token / refresh_token 쌍 발급.
    프론트 axios 인터셉터가 401 응답 시 자동으로 호출.
    Rate limit: 20회/분. 기존 refresh_token은 Redis에서 무효화(로테이션).

    Args:
        body.refresh_token (str) : 로그인 또는 이전 갱신에서 받은 refresh_token.

    Returns:
        access_token  (str) : 새 JWT. 만료 60분.
        refresh_token (str) : 새 refresh_token. 만료 7일.
        token_type    (str) : 항상 "bearer".

    Raises:
        401 : refresh_token 만료, 변조, 또는 Redis에서 블랙리스트 처리됨
        429 : Rate limit 초과 (20회/분)
    """
    return await auth_service.refresh(
        db=db,
        redis=redis,
        token=body.refresh_token,
        ip_address=_get_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )


@router.get("/me")
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [현재 사용자 조회] JWT 토큰에서 추출한 user_id로 사용자 정보 + 기관명 반환.
    프론트 초기 로딩 시 호출하여 사용자 역할(role) 및 기관명을 확인.

    Args:
        없음 (Authorization 헤더의 Bearer 토큰에서 자동 추출)

    Returns:
        user_id     (str) : 로그인한 사용자 UUID.
        name        (str) : 사용자 이름.
        role        (str) : 권한. "platform_admin" | "tenant_admin" | "social_worker"
        tenant_id   (str) : 소속 기관 UUID.
        tenant_name (str) : 소속 기관명.

    Raises:
        401 : 토큰 없음 또는 만료
    """
    user_result = await db.execute(
        select(User).where(User.id == uuid.UUID(current_user.user_id))
    )
    user = user_result.scalar_one_or_none()
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == uuid.UUID(current_user.tenant_id))
    )
    tenant = tenant_result.scalar_one_or_none()
    return {
        "user_id": current_user.user_id,
        "name": user.name if user else "",
        "role": current_user.role,
        "tenant_id": current_user.tenant_id,
        "tenant_name": tenant.name if tenant else "",
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def logout(
    request: Request,
    body: LogoutRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """
    [로그아웃] 전달받은 refresh_token을 Redis 블랙리스트에 등록해 재사용 차단.
    Rate limit: 20회/분. 감사 로그 기록.

    Args:
        body.refresh_token (str) : 로그아웃할 세션의 refresh_token.

    Returns:
        없음 (HTTP 204 No Content)

    Raises:
        401 : access_token 없음 또는 만료
        429 : Rate limit 초과 (20회/분)
    """
    await auth_service.logout(
        db=db,
        redis=redis,
        refresh_token_str=body.refresh_token,
        current_user_id=current_user.user_id,
        current_tenant_id=current_user.tenant_id,
        ip_address=_get_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

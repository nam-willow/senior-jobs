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
    await auth_service.logout(
        db=db,
        redis=redis,
        refresh_token_str=body.refresh_token,
        current_user_id=current_user.user_id,
        current_tenant_id=current_user.tenant_id,
        ip_address=_get_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

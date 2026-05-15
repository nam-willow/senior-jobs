import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    TokenReuseDetected,
    create_access_token,
    create_refresh_token,
    decode_token,
    rotate_refresh_token,
    revoke_all_user_tokens,
    revoke_refresh_token,
    store_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services.audit import record_audit


async def login(
    db: AsyncSession,
    redis: aioredis.Redis,
    *,
    email: str,
    password: str,
    ip_address: str,
    user_agent: str | None = None,
) -> TokenResponse:
    result = await db.execute(
        select(User).where(User.email == email, User.is_active.is_(True))
    )
    user: User | None = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role.value,
    )
    refresh_token, jti = create_refresh_token(user_id=str(user.id))
    await store_refresh_token(redis, user_id=str(user.id), jti=jti)

    await record_audit(
        db=db,
        tenant_id=str(user.tenant_id),
        user_id=str(user.id),
        action_type="LOGIN",
        target_table="users",
        target_id=str(user.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def refresh(
    db: AsyncSession,
    redis: aioredis.Redis,
    *,
    token: str,
    ip_address: str,
    user_agent: str | None = None,
) -> TokenResponse:
    try:
        user_id, old_jti = await verify_refresh_token(redis, token)
    except TokenReuseDetected as exc:
        compromised_user_id: str = exc.args[0]
        await revoke_all_user_tokens(redis, compromised_user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="보안 위협이 감지되었습니다. 다시 로그인해주세요.",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 Refresh Token입니다.",
        )

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.is_active.is_(True))
    )
    user: User | None = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다.",
        )

    new_refresh_token, _ = await rotate_refresh_token(
        redis, old_jti=old_jti, user_id=user_id
    )
    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role.value,
    )

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


async def logout(
    db: AsyncSession,
    redis: aioredis.Redis,
    *,
    refresh_token_str: str,
    current_user_id: str,
    current_tenant_id: str,
    ip_address: str,
    user_agent: str | None = None,
) -> None:
    try:
        payload = decode_token(refresh_token_str)
        jti: str | None = payload.get("jti")
        token_user_id: str | None = payload.get("sub")
    except JWTError:
        # 만료된 토큰이어도 로그아웃은 성공으로 처리
        jti = None
        token_user_id = None

    # 자신의 토큰만 폐기 허용
    if jti and token_user_id == current_user_id:
        await revoke_refresh_token(redis, jti=jti, user_id=current_user_id)

    await record_audit(
        db=db,
        tenant_id=current_tenant_id,
        user_id=current_user_id,
        action_type="LOGOUT",
        target_table="users",
        target_id=current_user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

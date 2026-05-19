from __future__ import annotations
from typing import Optional
import uuid
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── 패스워드 ─────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ──────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, tenant_id: str, role: str) -> str:
    expire = _now() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": _now(),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """(encoded_token, jti) 반환. jti는 Redis 키로 사용."""
    jti = str(uuid.uuid4())
    expire = _now() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": _now(),
        "jti": jti,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, jti


def decode_token(token: str) -> dict:
    """유효하지 않으면 JWTError 발생."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


# ── Redis 키 컨벤션 ───────────────────────────────────────────────────────────

def _rt_key(jti: str) -> str:
    return f"refresh_token:{jti}"


def _user_tokens_key(user_id: str) -> str:
    return f"user_tokens:{user_id}"


# ── Refresh Token Redis 관리 ─────────────────────────────────────────────────

async def store_refresh_token(redis: aioredis.Redis, user_id: str, jti: str) -> None:
    ttl = settings.refresh_token_expire_days * 86400
    pipe = redis.pipeline()
    pipe.setex(_rt_key(jti), ttl, user_id)
    pipe.sadd(_user_tokens_key(user_id), jti)
    pipe.expire(_user_tokens_key(user_id), ttl)
    await pipe.execute()


async def rotate_refresh_token(
    redis: aioredis.Redis,
    old_jti: str,
    user_id: str,
) -> tuple[str, str]:
    """
    이전 토큰 삭제 → 새 토큰 발급 → 저장.
    반환: (new_token, new_jti)
    """
    pipe = redis.pipeline()
    pipe.delete(_rt_key(old_jti))
    pipe.srem(_user_tokens_key(user_id), old_jti)
    await pipe.execute()

    new_token, new_jti = create_refresh_token(user_id)
    await store_refresh_token(redis, user_id, new_jti)
    return new_token, new_jti


async def revoke_all_user_tokens(redis: aioredis.Redis, user_id: str) -> None:
    """재사용 감지 시 해당 유저 전체 세션 강제 만료."""
    jtis = await redis.smembers(_user_tokens_key(user_id))
    if jtis:
        pipe = redis.pipeline()
        for jti in jtis:
            pipe.delete(_rt_key(jti.decode() if isinstance(jti, bytes) else jti))
        pipe.delete(_user_tokens_key(user_id))
        await pipe.execute()


async def get_user_id_by_refresh_jti(
    redis: aioredis.Redis, jti: str
) -> Optional[str]:
    """Redis에 jti가 없으면 None (만료 또는 재사용 시도)."""
    value = await redis.get(_rt_key(jti))
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else value


async def revoke_refresh_token(redis: aioredis.Redis, jti: str, user_id: str) -> None:
    """로그아웃 시 단일 토큰 무효화."""
    pipe = redis.pipeline()
    pipe.delete(_rt_key(jti))
    pipe.srem(_user_tokens_key(user_id), jti)
    await pipe.execute()


# ── Refresh Token 검증 흐름 ───────────────────────────────────────────────────

class TokenReuseDetected(Exception):
    """Refresh Token 재사용 감지 — 전체 세션 만료 처리 필요."""


async def verify_refresh_token(
    redis: aioredis.Redis, token: str
) -> tuple[str, str]:
    """
    검증 성공: (user_id, jti) 반환.
    재사용 감지: TokenReuseDetected 발생 (호출자가 revoke_all_user_tokens 처리).
    유효하지 않은 토큰: JWTError 발생.
    """
    try:
        payload = decode_token(token)
    except JWTError:
        raise

    if payload.get("type") != "refresh":
        raise JWTError("Not a refresh token")

    jti: str = payload["jti"]
    user_id: str = payload["sub"]

    stored_user_id = await get_user_id_by_refresh_jti(redis, jti)

    if stored_user_id is None:
        # Redis에 없음 → 이미 사용된 토큰 재사용 시도
        raise TokenReuseDetected(user_id)

    if stored_user_id != user_id:
        raise JWTError("Token user mismatch")

    return user_id, jti

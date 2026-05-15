from enum import IntEnum
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.security import decode_token

# ── 역할 정의 ─────────────────────────────────────────────────────────────────

class Role(str):
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN   = "tenant_admin"
    SOCIAL_WORKER  = "social_worker"
    APPROVER       = "approver"
    AUDITOR        = "auditor"
    VIEWER         = "viewer"


# 역할 계층 (높을수록 상위)
_ROLE_LEVEL: dict[str, int] = {
    Role.PLATFORM_ADMIN: 100,
    Role.TENANT_ADMIN:    80,
    Role.SOCIAL_WORKER:   60,
    Role.APPROVER:        60,
    Role.AUDITOR:         40,
    Role.VIEWER:          20,
}

ALL_ROLES = list(_ROLE_LEVEL.keys())


def role_level(role: str) -> int:
    return _ROLE_LEVEL.get(role, 0)


# ── 퍼미션 매트릭스 ───────────────────────────────────────────────────────────

PERMISSION_MATRIX: dict[str, list[str]] = {
    "VIEW_SENIOR":        [Role.PLATFORM_ADMIN, Role.TENANT_ADMIN, Role.SOCIAL_WORKER, Role.APPROVER, Role.AUDITOR, Role.VIEWER],
    "EDIT_SENIOR":        [Role.PLATFORM_ADMIN, Role.TENANT_ADMIN, Role.SOCIAL_WORKER],
    "DELETE_SENIOR":      [Role.PLATFORM_ADMIN, Role.TENANT_ADMIN],
    "EDIT_WORK_RECORD":   [Role.PLATFORM_ADMIN, Role.TENANT_ADMIN, Role.SOCIAL_WORKER],
    "APPROVE_RECORD":     [Role.PLATFORM_ADMIN, Role.TENANT_ADMIN, Role.APPROVER],
    "MANAGE_BUDGET":      [Role.PLATFORM_ADMIN, Role.TENANT_ADMIN],
    "EXPORT_PDF":         [Role.PLATFORM_ADMIN, Role.TENANT_ADMIN, Role.SOCIAL_WORKER, Role.APPROVER],
    "VIEW_AUDIT_LOG":     [Role.PLATFORM_ADMIN, Role.TENANT_ADMIN, Role.AUDITOR],
    "MANAGE_POLICY":      [Role.PLATFORM_ADMIN, Role.TENANT_ADMIN],
    "MANAGE_USERS":       [Role.PLATFORM_ADMIN, Role.TENANT_ADMIN],
    "EDIT_SESSION_HOURS": [Role.PLATFORM_ADMIN, Role.TENANT_ADMIN, Role.SOCIAL_WORKER],
}


def has_permission(role: str, permission: str) -> bool:
    return role in PERMISSION_MATRIX.get(permission, [])


# ── 토큰 파싱 ─────────────────────────────────────────────────────────────────

bearer_scheme = HTTPBearer()


class CurrentUser:
    def __init__(self, user_id: str, tenant_id: str, role: str, jti: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.jti = jti

    @property
    def is_platform_admin(self) -> bool:
        return self.role == Role.PLATFORM_ADMIN


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> CurrentUser:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise exc

    if payload.get("type") != "access":
        raise exc

    user_id: str | None = payload.get("sub")
    tenant_id: str | None = payload.get("tenant_id")
    role: str | None = payload.get("role")
    jti: str | None = payload.get("jti")

    if not all([user_id, tenant_id, role, jti]):
        raise exc

    return CurrentUser(user_id=user_id, tenant_id=tenant_id, role=role, jti=jti)


# ── 역할 의존성 팩토리 ────────────────────────────────────────────────────────

def require_role(*roles: str):
    """지정한 역할 중 하나 이상이어야 통과. 계층 상위 역할도 자동 허용."""
    min_level = min(role_level(r) for r in roles)

    async def dependency(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if role_level(current_user.role) < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency


def require_permission(permission: str):
    """PERMISSION_MATRIX 기준 퍼미션 체크."""
    async def dependency(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user

    return dependency


# ── 자주 쓰는 의존성 단축 ─────────────────────────────────────────────────────

RequireAuth        = Depends(get_current_user)
RequireTenantAdmin = Depends(require_role(Role.PLATFORM_ADMIN, Role.TENANT_ADMIN))
RequirePlatform    = Depends(require_role(Role.PLATFORM_ADMIN))

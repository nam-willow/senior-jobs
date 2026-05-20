"""PM-* Permissions + core unit tests."""
from __future__ import annotations
import uuid
from unittest.mock import patch, AsyncMock

import pytest

from app.core.permissions import (
    CurrentUser,
    Role,
    ALL_ROLES,
    PERMISSION_MATRIX,
    has_permission,
    role_level,
    require_permission,
    require_role,
    get_current_user,
)


# ── PM-01: role_level values ──────────────────────────────────────────────────

def test_pm01_role_levels():
    assert role_level(Role.PLATFORM_ADMIN) == 100
    assert role_level(Role.TENANT_ADMIN) == 80
    assert role_level(Role.SOCIAL_WORKER) == 60
    assert role_level(Role.APPROVER) == 60
    assert role_level(Role.AUDITOR) == 40
    assert role_level(Role.VIEWER) == 20
    assert role_level("unknown_role") == 0


# ── PM-02: has_permission for each role ──────────────────────────────────────

def test_pm02_has_permission_platform_admin():
    for perm in PERMISSION_MATRIX:
        assert has_permission(Role.PLATFORM_ADMIN, perm), f"platform_admin missing {perm}"


def test_pm03_has_permission_tenant_admin():
    for perm in PERMISSION_MATRIX:
        assert has_permission(Role.TENANT_ADMIN, perm), f"tenant_admin missing {perm}"


def test_pm04_viewer_limited_permissions():
    assert has_permission(Role.VIEWER, "VIEW_SENIOR") is True
    assert has_permission(Role.VIEWER, "DELETE_SENIOR") is False
    assert has_permission(Role.VIEWER, "MANAGE_BUDGET") is False
    assert has_permission(Role.VIEWER, "MANAGE_POLICY") is False


def test_pm05_social_worker_permissions():
    assert has_permission(Role.SOCIAL_WORKER, "EDIT_SENIOR") is True
    assert has_permission(Role.SOCIAL_WORKER, "VIEW_SENIOR") is True
    assert has_permission(Role.SOCIAL_WORKER, "DELETE_SENIOR") is False
    assert has_permission(Role.SOCIAL_WORKER, "APPROVE_RECORD") is False


def test_pm06_approver_permissions():
    assert has_permission(Role.APPROVER, "APPROVE_RECORD") is True
    assert has_permission(Role.APPROVER, "VIEW_SENIOR") is True
    assert has_permission(Role.APPROVER, "EDIT_SENIOR") is False
    assert has_permission(Role.APPROVER, "MANAGE_USERS") is False


def test_pm07_auditor_permissions():
    assert has_permission(Role.AUDITOR, "VIEW_AUDIT_LOG") is True
    assert has_permission(Role.AUDITOR, "VIEW_SENIOR") is True
    assert has_permission(Role.AUDITOR, "EDIT_SENIOR") is False


def test_pm08_unknown_permission():
    assert has_permission(Role.PLATFORM_ADMIN, "NON_EXISTENT_PERM") is False


# ── PM-09: CurrentUser ───────────────────────────────────────────────────────

def test_pm09_current_user_attrs():
    user = CurrentUser(
        user_id="u1", tenant_id="t1", role="platform_admin", jti="j1"
    )
    assert user.user_id == "u1"
    assert user.tenant_id == "t1"
    assert user.role == "platform_admin"
    assert user.jti == "j1"
    assert user.is_platform_admin is True


def test_pm10_current_user_not_platform_admin():
    user = CurrentUser(user_id="u2", tenant_id="t2", role="tenant_admin", jti="j2")
    assert user.is_platform_admin is False


# ── PM-11: ALL_ROLES contains expected roles ──────────────────────────────────

def test_pm11_all_roles():
    assert Role.PLATFORM_ADMIN in ALL_ROLES
    assert Role.TENANT_ADMIN in ALL_ROLES
    assert Role.SOCIAL_WORKER in ALL_ROLES
    assert Role.APPROVER in ALL_ROLES
    assert Role.AUDITOR in ALL_ROLES
    assert Role.VIEWER in ALL_ROLES


# ── PM-12: require_role closure ───────────────────────────────────────────────

async def test_pm12_require_role_pass():
    """require_role dependency passes when user has sufficient level."""
    from fastapi import HTTPException
    dep = require_role(Role.TENANT_ADMIN)
    user = CurrentUser(user_id="u1", tenant_id="t1", role="platform_admin", jti="j")
    # Mock get_current_user to return our user
    result = await dep(current_user=user)
    assert result is user


async def test_pm13_require_role_fail():
    """require_role raises 403 when role level is too low."""
    from fastapi import HTTPException
    dep = require_role(Role.PLATFORM_ADMIN)
    user = CurrentUser(user_id="u1", tenant_id="t1", role="viewer", jti="j")
    with pytest.raises(HTTPException) as exc:
        await dep(current_user=user)
    assert exc.value.status_code == 403


# ── PM-14: require_permission closure ────────────────────────────────────────

async def test_pm14_require_permission_pass():
    from fastapi import HTTPException
    dep = require_permission("VIEW_SENIOR")
    user = CurrentUser(user_id="u1", tenant_id="t1", role="viewer", jti="j")
    result = await dep(current_user=user)
    assert result is user


async def test_pm15_require_permission_fail():
    from fastapi import HTTPException
    dep = require_permission("DELETE_SENIOR")
    user = CurrentUser(user_id="u1", tenant_id="t1", role="viewer", jti="j")
    with pytest.raises(HTTPException) as exc:
        await dep(current_user=user)
    assert exc.value.status_code == 403


# ── PM-16: get_current_user token parsing ────────────────────────────────────

async def test_pm16_get_current_user_no_credentials():
    """get_current_user raises 401 when no token provided."""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=None)
    assert exc.value.status_code == 401


async def test_pm17_get_current_user_valid_token():
    """get_current_user succeeds with valid JWT."""
    from app.core.security import create_access_token
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        role="tenant_admin",
    )
    from fastapi.security import HTTPAuthorizationCredentials
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await get_current_user(credentials=creds)
    assert user.role == "tenant_admin"


async def test_pm18_get_current_user_wrong_type():
    """get_current_user raises 401 when token type is refresh."""
    from app.core.config import settings
    from fastapi.security import HTTPAuthorizationCredentials
    from fastapi import HTTPException
    from jose import jwt as _jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "role": "tenant_admin",
        "jti": str(uuid.uuid4()),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = _jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=creds)
    assert exc.value.status_code == 401

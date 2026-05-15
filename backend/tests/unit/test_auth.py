"""
Phase 1 인증 단위 테스트 (TC-AUTH-01 ~ 05)
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import make_app


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db, redis_mock, test_user):
    app = make_app(db, redis_mock)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac, test_user


# ── TC-AUTH-01: 로그인 성공 ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client):
    ac, user = client
    resp = await ac.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": "Test1234!",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


# ── TC-AUTH-02: 잘못된 비밀번호 ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    ac, user = client
    resp = await ac.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": "WrongPass!",
    })
    assert resp.status_code == 401


# ── TC-AUTH-03: Refresh Token Rotation ────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_token_rotation(client):
    ac, user = client

    # 로그인
    login_resp = await ac.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": "Test1234!",
    })
    tokens = login_resp.json()
    old_refresh = tokens["refresh_token"]

    # Refresh → 새 토큰 쌍
    refresh_resp = await ac.post("/api/v1/auth/refresh", json={
        "refresh_token": old_refresh,
    })
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert new_tokens["refresh_token"] != old_refresh
    assert new_tokens["access_token"] != tokens["access_token"]


# ── TC-AUTH-04: Refresh Token 재사용 감지 → 전체 세션 만료 ──────────────────

@pytest.mark.asyncio
async def test_refresh_token_reuse_detection(client):
    ac, user = client

    # 로그인
    login_resp = await ac.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": "Test1234!",
    })
    old_refresh = login_resp.json()["refresh_token"]

    # 정상 refresh → old_refresh 무효화
    await ac.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})

    # old_refresh 재사용 → 보안 감지 → 401
    reuse_resp = await ac.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse_resp.status_code == 401
    assert "보안" in reuse_resp.json()["detail"]


# ── TC-AUTH-05: 로그아웃 ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout(client):
    ac, user = client

    # 로그인
    login_resp = await ac.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": "Test1234!",
    })
    tokens = login_resp.json()

    # 로그아웃
    logout_resp = await ac.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout_resp.status_code == 204

    # 로그아웃 후 해당 refresh token 재사용 불가
    retry_resp = await ac.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert retry_resp.status_code == 401

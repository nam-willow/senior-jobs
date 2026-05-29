from __future__ import annotations
from datetime import date
from typing import Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, RequireTenantAdmin, get_current_user
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_summary(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    year: Optional[int] = None,
):
    """
    [대시보드 요약] 연도별 사업단 유형별 예산 집행 현황 및 어르신 인원 통계 반환.
    대시보드 진입 시 가장 먼저 호출되는 핵심 집계 API.

    Args:
        year (int, optional) : 조회 연도. 생략 시 현재 연도 자동 적용.

    Returns:
        summary (List[dict]) : 사업단 유형별 집계.
            - bu_type        (str) : 사업단 유형. "public_benefit" | "social_service" | "market"
            - senior_count   (int) : 해당 유형 활성 어르신 수.
            - total_budget   (int) : 총 예산 합계 (어르신임금 + 담당자임금 + 운영비), 단위: 원.
            - total_spent    (int) : 총 지출 합계, 단위: 원.
            - remaining      (int) : 잔액 (total_budget - total_spent), 단위: 원.
            - achievement_pct(int) : 집행률 (0~100%).

    Raises:
        401 : 토큰 없음 또는 만료
    """
    if year is None:
        year = date.today().year
    return await dashboard_service.get_summary(db, current_user.tenant_id, year)


@router.get("/alerts")
async def get_alerts(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    year: Optional[int] = None,
):
    """
    [대시보드 알림] 초과근무·예산 경고·미제출 등 주의 필요 항목 목록 반환.
    대시보드 알림 카드와 알림(Alerts) 페이지에서 공통 사용.

    Args:
        year (int, optional) : 조회 연도. 생략 시 현재 연도 자동 적용.

    Returns:
        alerts (List[dict]) : 알림 목록.
            - id    (str) : 알림 식별자.
            - tone  (str) : 심각도. "danger" | "warm" | "gold" | "info"
            - title (str) : 알림 제목.
            - meta  (str) : 부가 설명.
            - goto  (str) : 클릭 시 이동할 페이지.
            - tab   (str, nullable) : 이동 시 선택할 탭.

    Raises:
        401 : 토큰 없음 또는 만료
    """
    if year is None:
        year = date.today().year
    return await dashboard_service.get_alerts(db, current_user.tenant_id, year)


@router.get("/monthly-hours")
async def get_monthly_hours(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    year: Optional[int] = None,
):
    """
    [월별 근무시간] 1~11월 각 월의 승인된 근무시간 합계 반환.
    대시보드 BarChart(Recharts) 시각화에 사용.

    Args:
        year (int, optional) : 조회 연도. 생략 시 현재 연도 자동 적용.

    Returns:
        monthly (List[dict]) : 월별 데이터 배열 (1월~11월).
            - month        (int)   : 월 (1~11).
            - total_hours  (float) : 해당 월 전체 어르신 승인 근무시간 합계.

    Raises:
        401 : 토큰 없음 또는 만료
    """
    if year is None:
        year = date.today().year
    return await dashboard_service.get_monthly_hours(db, current_user.tenant_id, year)


@router.get("/kpi")
async def get_kpi(
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [KPI 지표] 관리자 전용. 예산 소진율·인원 목표 달성률 등 핵심 성과 지표 반환.
    TENANT_ADMIN 권한만 접근 가능. 연도 파라미터 없이 현재 연도 기준으로 계산.

    Args:
        없음 (토큰에서 tenant_id 자동 추출)

    Returns:
        KPI 집계 객체 (dashboard_service.get_kpi 반환값).

    Raises:
        401 : 토큰 없음 또는 만료
        403 : TENANT_ADMIN 권한 없음 (SOCIAL_WORKER 접근 불가)
    """
    return await dashboard_service.get_kpi(db, current_user.tenant_id)

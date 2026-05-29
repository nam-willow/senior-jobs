from __future__ import annotations
import uuid
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, require_permission
from app.models.annual_budget import AnnualBudget
from app.models.business_unit import BusinessUnit
from app.schemas.budget import (
    AnnualBudgetCreate,
    AnnualBudgetResponse,
    AnnualBudgetUpdate,
    ExpenditureCreate,
    ExpenditureResponse,
)
from app.schemas.common import PaginatedResponse
from app.services import budget_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


# Static-prefix routes MUST come before parameterised two-segment routes
# to avoid Starlette matching /expenditures/{id} as /{business_unit_id}/{year}.

@router.get("/check")
async def check_budget(
    year: int,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_BUDGET"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [예산 존재 여부 확인] 해당 연도에 등록된 예산이 있는지 여부만 반환.
    대시보드·예산 페이지 진입 시 예산 등록 안내 배너 표시 여부 결정에 사용.

    Args:
        year (int, query) : 확인할 연도. 필수. 예) 2026

    Returns:
        has_budget (bool) : True이면 해당 연도에 예산 1건 이상 등록됨.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_BUDGET 권한 없음
    """
    tenant_uuid = uuid.UUID(current_user.tenant_id)
    result = await db.execute(
        select(func.count()).select_from(AnnualBudget).join(
            BusinessUnit, AnnualBudget.business_unit_id == BusinessUnit.id
        ).where(
            AnnualBudget.tenant_id == tenant_uuid,
            AnnualBudget.year == year,
            BusinessUnit.is_active.is_(True),
        )
    )
    count = result.scalar_one()
    return {"has_budget": count > 0}


@router.get("/expenditures/{budget_id}", response_model=PaginatedResponse[ExpenditureResponse])
async def list_expenditures(
    budget_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_BUDGET"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [지출 내역 목록] 특정 예산의 지출 내역 전체 조회.
    BudgetStrip의 "사용 금액" 계산 및 예산 관리 페이지 지출 탭에서 사용.

    Args:
        budget_id (str, path) : 조회할 예산 UUID (AnnualBudget.id).

    Returns:
        items (List[ExpenditureResponse]) : 지출 내역 목록.
            - category    (str)  : 지출 구분. "wage" | "manager_wage" | "operation"
            - item_name   (str)  : 지출 항목명.
            - amount      (int)  : 지출 금액 (원).
            - expense_date(str)  : 지출일. 형식: "YYYY-MM-DD"
        total (int) : 전체 건수.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_BUDGET 권한 없음
    """
    items = await budget_service.list_expenditures(db, str(budget_id), current_user.tenant_id)
    return {"items": items, "total": len(items)}


@router.post("/expenditures/", response_model=ExpenditureResponse, status_code=status.HTTP_201_CREATED)
async def create_expenditure(
    data: ExpenditureCreate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_BUDGET"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [지출 등록] 예산에 지출 내역 추가. 감사 로그(IP 포함) 기록.
    등록 후 BudgetStrip 사용 금액 및 집행률에 즉시 반영됨.

    Args:
        data.annual_budget_id (str)          : 지출을 추가할 예산 UUID. 필수.
        data.category         (str)          : 지출 구분. 필수.
                                               "wage" | "manager_wage" | "operation"
        data.item_name        (str)          : 지출 항목명. 필수. 예) "3월 어르신 급여"
        data.amount           (int)          : 지출 금액 (원). 필수.
        data.expense_date     (str, date)    : 지출일. 필수. 형식: "YYYY-MM-DD"
        data.note             (str, optional): 비고.

    Returns:
        ExpenditureResponse : 등록된 지출 내역.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_BUDGET 권한 없음
        422 : 필수 항목 누락 또는 형식 오류
    """
    exp, warnings = await budget_service.create_expenditure(
        db, current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(exp)
    return exp


@router.delete("/expenditures/{exp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expenditure(
    exp_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_BUDGET"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [지출 삭제] 지출 내역 소프트 삭제. 감사 로그(IP 포함) 기록.

    Args:
        exp_id (str, path) : 삭제할 지출 내역 UUID.

    Returns:
        없음 (HTTP 204 No Content)

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_BUDGET 권한 없음
        404 : 지출 내역 없음
    """
    await budget_service.delete_expenditure(
        db, str(exp_id), current_user.tenant_id, current_user.user_id,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()


@router.get("/by-type/{bu_type}/{year}", response_model=AnnualBudgetResponse)
async def get_budget_by_type(
    bu_type: str,
    year: int,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_BUDGET"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [예산 조회 - 유형별] 사업단 유형과 연도로 예산 단건 조회.
    BudgetStrip 컴포넌트에서 탭(공익활동형·사회서비스형·시장형) 전환 시 호출.

    Args:
        bu_type (str, path) : 사업단 유형. "public_benefit" | "social_service" | "market"
        year    (int, path) : 조회 연도.

    Returns:
        AnnualBudgetResponse :
            - id                  (str) : 예산 UUID.
            - total_wage_budget   (int) : 어르신 임금 예산 (원).
            - manager_wage_budget (int) : 담당자 임금 예산 (원).
            - operation_budget    (int) : 사업진행비 예산 (원).
            - senior_count        (int) : 목표 어르신 인원.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_BUDGET 권한 없음
        404 : 해당 유형·연도의 예산 미등록
    """
    budget = await budget_service.get_budget_by_type(db, current_user.tenant_id, bu_type, year)

    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.get("/{business_unit_id}/{year}", response_model=AnnualBudgetResponse)
async def get_budget(
    business_unit_id: uuid.UUID,
    year: int,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_BUDGET"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [예산 조회 - 사업단별] 특정 사업단 UUID와 연도로 예산 단건 조회.

    Args:
        business_unit_id (str, path) : 사업단 UUID.
        year             (int, path) : 조회 연도.

    Returns:
        AnnualBudgetResponse : 예산 상세.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_BUDGET 권한 없음
        404 : 해당 사업단·연도의 예산 미등록
    """
    return await budget_service.get_budget(
        db, str(business_unit_id), year, current_user.tenant_id
    )


@router.post("/", response_model=AnnualBudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: AnnualBudgetCreate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_BUDGET"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [예산 등록] 사업단 + 연도 단위로 연간 예산 신규 등록. 감사 로그(IP 포함) 기록.

    Args:
        data.business_unit_id     (str) : 사업단 UUID. 필수.
        data.year                 (int) : 예산 연도. 필수.
        data.total_wage_budget    (int) : 어르신 임금 예산 (원). 필수.
        data.manager_wage_budget  (int) : 담당자 임금 예산 (원). 필수.
        data.operation_budget     (int) : 사업진행비 예산 (원). 필수.
        data.senior_count         (int) : 목표 어르신 인원. 필수.

    Returns:
        AnnualBudgetResponse : 등록된 예산.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_BUDGET 권한 없음
        422 : 필수 항목 누락
    """
    budget = await budget_service.create_budget(
        db, current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(budget)
    return budget


@router.put("/{budget_id}", response_model=AnnualBudgetResponse)
async def update_budget(
    budget_id: uuid.UUID,
    data: AnnualBudgetUpdate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_BUDGET"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    """
    [예산 수정] 등록된 예산 금액 부분 수정. 감사 로그(IP 포함) 기록.
    전달하지 않은 필드는 기존 값 유지.

    Args:
        budget_id                 (str, path)    : 수정할 예산 UUID.
        data.total_wage_budget    (int, optional): 변경할 어르신 임금 예산 (원).
        data.manager_wage_budget  (int, optional): 변경할 담당자 임금 예산 (원).
        data.operation_budget     (int, optional): 변경할 사업진행비 예산 (원).
        data.senior_count         (int, optional): 변경할 목표 어르신 인원.

    Returns:
        AnnualBudgetResponse : 수정된 예산.

    Raises:
        401 : 토큰 없음 또는 만료
        403 : MANAGE_BUDGET 권한 없음
        404 : 예산 없음
    """
    budget = await budget_service.update_budget(
        db, str(budget_id), current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(budget)
    return budget

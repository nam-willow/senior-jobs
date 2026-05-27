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
    """Returns {"has_budget": bool} — true if the tenant has at least one budget for the given year."""
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
    items = await budget_service.list_expenditures(db, str(budget_id), current_user.tenant_id)
    return {"items": items, "total": len(items)}


@router.post("/expenditures/", response_model=ExpenditureResponse, status_code=status.HTTP_201_CREATED)
async def create_expenditure(
    data: ExpenditureCreate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("MANAGE_BUDGET"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
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
    budget = await budget_service.update_budget(
        db, str(budget_id), current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(budget)
    return budget

from __future__ import annotations
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annual_budget import AnnualBudget
from app.models.budget_expenditure import BudgetExpenditure
from app.schemas.budget import AnnualBudgetCreate, AnnualBudgetUpdate, ExpenditureCreate
from app.services.audit import record_audit


async def create_budget(
    db: AsyncSession, tenant_id: str, user_id: str, data: AnnualBudgetCreate,
    ip_address: str, user_agent: str = "",
) -> AnnualBudget:
    budget = AnnualBudget(
        tenant_id=uuid.UUID(tenant_id),
        business_unit_id=data.business_unit_id,
        year=data.year,
        total_wage_budget=data.total_wage_budget,
        manager_wage_budget=data.manager_wage_budget,
        operation_budget=data.operation_budget,
        senior_count=data.senior_count,
        created_by=uuid.UUID(user_id),
    )
    db.add(budget)
    await db.flush()
    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="CREATE", target_table="annual_budgets",
        target_id=str(budget.id),
        after_data={"year": data.year, "total_wage_budget": data.total_wage_budget},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.refresh(budget)
    return budget


async def get_budget(
    db: AsyncSession, business_unit_id: str, year: int, tenant_id: str
) -> AnnualBudget:
    result = await db.execute(
        select(AnnualBudget).where(
            AnnualBudget.business_unit_id == uuid.UUID(business_unit_id),
            AnnualBudget.year == year,
            AnnualBudget.tenant_id == uuid.UUID(tenant_id),
        )
    )
    budget = result.scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget


async def update_budget(
    db: AsyncSession, budget_id: str, tenant_id: str, user_id: str,
    data: AnnualBudgetUpdate, ip_address: str, user_agent: str = "",
) -> AnnualBudget:
    result = await db.execute(
        select(AnnualBudget).where(
            AnnualBudget.id == uuid.UUID(budget_id),
            AnnualBudget.tenant_id == uuid.UUID(tenant_id),
        )
    )
    budget = result.scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    before = {
        "total_wage_budget": budget.total_wage_budget,
        "senior_count": budget.senior_count,
    }
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(budget, field, value)

    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="UPDATE", target_table="annual_budgets",
        target_id=budget_id, before_data=before,
        after_data=data.model_dump(exclude_unset=True),
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.flush()
    await db.refresh(budget)
    return budget


async def create_expenditure(
    db: AsyncSession, tenant_id: str, user_id: str, data: ExpenditureCreate,
    ip_address: str, user_agent: str = "",
) -> tuple[BudgetExpenditure, list[str]]:
    # 잔액 확인
    budget_result = await db.execute(
        select(AnnualBudget).where(
            AnnualBudget.id == data.annual_budget_id,
            AnnualBudget.tenant_id == uuid.UUID(tenant_id),
        )
    )
    budget = budget_result.scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    exp = BudgetExpenditure(
        tenant_id=uuid.UUID(tenant_id),
        annual_budget_id=data.annual_budget_id,
        category=data.category,
        item_name=data.item_name,
        amount=data.amount,
        expense_date=data.expense_date,
        note=data.note,
        created_by=uuid.UUID(user_id),
    )
    db.add(exp)
    await db.flush()

    warnings: list[str] = []
    # 잔액 계산 (category별)
    from sqlalchemy import func as sqlfunc
    spent_result = await db.execute(
        select(sqlfunc.coalesce(sqlfunc.sum(BudgetExpenditure.amount), 0)).where(
            BudgetExpenditure.annual_budget_id == data.annual_budget_id,
            BudgetExpenditure.category == data.category,
        )
    )
    total_spent = int(spent_result.scalar())
    category_budget = {
        "wage": budget.total_wage_budget,
        "manager_wage": budget.manager_wage_budget,
        "operation": budget.operation_budget,
    }.get(data.category.value, 0)

    if total_spent > category_budget:
        warnings.append(f"사업비 잔액 마이너스: {total_spent - category_budget:,}원 초과")

    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="CREATE", target_table="budget_expenditures",
        target_id=str(exp.id),
        after_data={"category": data.category.value, "amount": data.amount},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.refresh(exp)
    return exp, warnings


async def list_expenditures(
    db: AsyncSession, budget_id: str, tenant_id: str
) -> list[BudgetExpenditure]:
    result = await db.execute(
        select(BudgetExpenditure).where(
            BudgetExpenditure.annual_budget_id == uuid.UUID(budget_id),
            BudgetExpenditure.tenant_id == uuid.UUID(tenant_id),
        )
    )
    return list(result.scalars().all())


async def delete_expenditure(
    db: AsyncSession, exp_id: str, tenant_id: str, user_id: str,
    ip_address: str, user_agent: str = "",
) -> None:
    result = await db.execute(
        select(BudgetExpenditure).where(
            BudgetExpenditure.id == uuid.UUID(exp_id),
            BudgetExpenditure.tenant_id == uuid.UUID(tenant_id),
        )
    )
    exp = result.scalar_one_or_none()
    if exp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expenditure not found")
    exp.soft_delete(uuid.UUID(user_id))
    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="DELETE", target_table="budget_expenditures",
        target_id=exp_id, ip_address=ip_address, user_agent=user_agent,
    )
    await db.flush()

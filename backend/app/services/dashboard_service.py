from __future__ import annotations
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annual_budget import AnnualBudget
from app.models.budget_expenditure import BudgetExpenditure
from app.models.business_unit import BusinessUnit, BusinessUnitType
from app.models.senior import Senior


TYPE_LABELS = {
    BusinessUnitType.PUBLIC_BENEFIT.value: "공익활동형",
    BusinessUnitType.SOCIAL_SERVICE.value: "사회서비스형",
    BusinessUnitType.MARKET.value: "시장형",
}


async def get_summary(db: AsyncSession, tenant_id: str, year: int) -> dict:
    summary = []
    for bu_type in BusinessUnitType:
        # 사업단 목록
        bu_result = await db.execute(
            select(BusinessUnit).where(
                BusinessUnit.tenant_id == uuid.UUID(tenant_id),
                BusinessUnit.type == bu_type,
                BusinessUnit.year == year,
                BusinessUnit.is_active.is_(True),
            )
        )
        bus = list(bu_result.scalars().all())
        bu_ids = [bu.id for bu in bus]

        total_budget = sum(
            bu.total_annual_hours * 0 for bu in bus  # placeholder
        )
        total_expenditure = 0
        wage_budget = 0
        wage_spent = 0
        mgr_budget = 0
        mgr_spent = 0
        op_budget = 0
        op_spent = 0
        senior_count = 0

        if bu_ids:
            # 예산 합계
            ab_result = await db.execute(
                select(AnnualBudget).where(
                    AnnualBudget.business_unit_id.in_(bu_ids),
                    AnnualBudget.year == year,
                    AnnualBudget.tenant_id == uuid.UUID(tenant_id),
                )
            )
            budgets = list(ab_result.scalars().all())
            wage_budget = sum(b.total_wage_budget for b in budgets)
            mgr_budget = sum(b.manager_wage_budget for b in budgets)
            op_budget = sum(b.operation_budget for b in budgets)
            senior_count = sum(b.senior_count for b in budgets)
            total_budget = wage_budget + mgr_budget + op_budget

            budget_ids = [b.id for b in budgets]
            if budget_ids:
                for category, field_name in [("wage", "wage_spent"), ("manager_wage", "mgr_spent"), ("operation", "op_spent")]:
                    exp_result = await db.execute(
                        select(func.coalesce(func.sum(BudgetExpenditure.amount), 0)).where(
                            BudgetExpenditure.annual_budget_id.in_(budget_ids),
                            BudgetExpenditure.category == category,
                            BudgetExpenditure.tenant_id == uuid.UUID(tenant_id),
                        )
                    )
                    val = int(exp_result.scalar())
                    if category == "wage":
                        wage_spent = val
                    elif category == "manager_wage":
                        mgr_spent = val
                    else:
                        op_spent = val
                total_expenditure = wage_spent + mgr_spent + op_spent

        remaining = total_budget - total_expenditure
        achievement_rate = round(total_expenditure / total_budget * 100, 1) if total_budget > 0 else 0.0

        def rate(spent, budget):
            return round(spent / budget * 100, 1) if budget > 0 else 0.0

        summary.append({
            "type": bu_type.value,
            "type_label": TYPE_LABELS[bu_type.value],
            "total_budget": total_budget,
            "total_expenditure": total_expenditure,
            "remaining": remaining,
            "achievement_rate": achievement_rate,
            "senior_count": senior_count,
            "breakdown": {
                "wage":         {"budget": wage_budget, "spent": wage_spent, "rate": rate(wage_spent, wage_budget)},
                "manager_wage": {"budget": mgr_budget,  "spent": mgr_spent,  "rate": rate(mgr_spent, mgr_budget)},
                "operation":    {"budget": op_budget,   "spent": op_spent,   "rate": rate(op_spent, op_budget)},
            },
        })

    return {"year": year, "summary": summary}


async def get_kpi(db: AsyncSession, tenant_id: str) -> dict:
    year = date.today().year
    senior_count_result = await db.execute(
        select(func.count(Senior.id)).where(
            Senior.tenant_id == uuid.UUID(tenant_id),
            Senior.is_active.is_(True),
        )
    )
    senior_count = int(senior_count_result.scalar())
    return {"year": year, "active_senior_count": senior_count}

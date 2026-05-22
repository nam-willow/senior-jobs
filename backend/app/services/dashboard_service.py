from __future__ import annotations
import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annual_budget import AnnualBudget
from app.models.budget_expenditure import BudgetExpenditure
from app.models.business_unit import BusinessUnit, BusinessUnitType
from app.models.consultation_log import ConsultationLog
from app.models.monthly_work_records import MonthlyWorkRecord, WorkRecordStatus
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

        total_budget = 0
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


async def get_alerts(db: AsyncSession, tenant_id: str, year: int) -> dict:
    alerts = []
    today = date.today()
    tenant_uuid = uuid.UUID(tenant_id)

    # 1. 30일 이상 상담 없는 어르신
    seniors_result = await db.execute(
        select(Senior).where(
            Senior.tenant_id == tenant_uuid,
            Senior.is_active.is_(True),
        ).limit(100)
    )
    for senior in seniors_result.scalars().all():
        last_result = await db.execute(
            select(func.max(ConsultationLog.consultation_date)).where(
                ConsultationLog.senior_id == senior.id,
                ConsultationLog.deleted_at.is_(None),
            )
        )
        last_dt = last_result.scalar()
        ref = last_dt.date() if last_dt else senior.created_at.date()
        days = (today - ref).days
        if days >= 30:
            alerts.append({
                "id": f"consult_{senior.id}",
                "tone": "danger",
                "title": f"{senior.name} 어르신 {days}일째 상담 없음",
                "meta": "상담일지 미등록",
                "goto": "consult",
            })

    # 2. 예산 90% 이상 소진
    for bu_type in BusinessUnitType:
        bu_result = await db.execute(
            select(BusinessUnit).where(
                BusinessUnit.tenant_id == tenant_uuid,
                BusinessUnit.type == bu_type,
                BusinessUnit.year == year,
                BusinessUnit.is_active.is_(True),
            )
        )
        bus = list(bu_result.scalars().all())
        bu_ids = [bu.id for bu in bus]
        if not bu_ids:
            continue
        ab_result = await db.execute(
            select(AnnualBudget).where(
                AnnualBudget.business_unit_id.in_(bu_ids),
                AnnualBudget.year == year,
                AnnualBudget.tenant_id == tenant_uuid,
            )
        )
        budgets = list(ab_result.scalars().all())
        if not budgets:
            continue
        total_budget = sum(b.total_wage_budget + b.manager_wage_budget + b.operation_budget for b in budgets)
        budget_ids = [b.id for b in budgets]
        exp_result = await db.execute(
            select(func.coalesce(func.sum(BudgetExpenditure.amount), 0)).where(
                BudgetExpenditure.annual_budget_id.in_(budget_ids),
                BudgetExpenditure.tenant_id == tenant_uuid,
            )
        )
        total_spent = int(exp_result.scalar() or 0)
        if total_budget > 0:
            pct = round(total_spent / total_budget * 100)
            if pct >= 90:
                label = TYPE_LABELS.get(bu_type.value, bu_type.value)
                alerts.append({
                    "id": f"budget_{bu_type.value}",
                    "tone": "warm",
                    "title": f"{label} 예산 {pct}% 소진",
                    "meta": f"잔액 {total_budget - total_spent:,}원",
                    "goto": "budget",
                })

    # 3. 결재 대기 건수
    pending_result = await db.execute(
        select(func.count()).select_from(MonthlyWorkRecord).where(
            MonthlyWorkRecord.tenant_id == tenant_uuid,
            MonthlyWorkRecord.status == WorkRecordStatus.SUBMITTED,
            MonthlyWorkRecord.deleted_at.is_(None),
        )
    )
    pending_count = pending_result.scalar_one()
    if pending_count > 0:
        alerts.append({
            "id": "approvals",
            "tone": "info",
            "title": f"결재 대기 {pending_count}건",
            "meta": "월별 근무기록 승인 필요",
            "goto": "approvals",
        })

    return {"alerts": alerts, "year": year}


async def get_monthly_hours(db: AsyncSession, tenant_id: str, year: int) -> dict:
    tenant_uuid = uuid.UUID(tenant_id)
    type_keys = [
        (BusinessUnitType.PUBLIC_BENEFIT, "pub"),
        (BusinessUnitType.SOCIAL_SERVICE, "svc"),
        (BusinessUnitType.MARKET, "mkt"),
    ]
    monthly = []
    for month in range(1, 13):
        row: dict = {"m": f"{month}월"}
        for bu_type, key in type_keys:
            bu_ids_result = await db.execute(
                select(BusinessUnit.id).where(
                    BusinessUnit.tenant_id == tenant_uuid,
                    BusinessUnit.type == bu_type,
                    BusinessUnit.year == year,
                    BusinessUnit.is_active.is_(True),
                )
            )
            bu_ids = [r[0] for r in bu_ids_result.all()]
            if bu_ids:
                h = await db.execute(
                    select(func.coalesce(func.sum(MonthlyWorkRecord.worked_hours), 0))
                    .join(Senior, MonthlyWorkRecord.senior_id == Senior.id)
                    .where(
                        MonthlyWorkRecord.tenant_id == tenant_uuid,
                        MonthlyWorkRecord.year == year,
                        MonthlyWorkRecord.month == month,
                        MonthlyWorkRecord.deleted_at.is_(None),
                        Senior.business_unit_id.in_(bu_ids),
                    )
                )
                row[key] = float(h.scalar() or 0)
            else:
                row[key] = 0
        monthly.append(row)
    return {"year": year, "monthly": monthly}


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

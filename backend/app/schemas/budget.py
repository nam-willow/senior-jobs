from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.budget_expenditure import BudgetCategory


class AnnualBudgetCreate(BaseModel):
    business_unit_id: uuid.UUID
    year: int
    total_wage_budget: int
    manager_wage_budget: int
    operation_budget: int
    senior_count: int


class AnnualBudgetUpdate(BaseModel):
    total_wage_budget: Optional[int] = None
    manager_wage_budget: Optional[int] = None
    operation_budget: Optional[int] = None
    senior_count: Optional[int] = None


class AnnualBudgetResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    business_unit_id: uuid.UUID
    year: int
    total_wage_budget: int
    manager_wage_budget: int
    operation_budget: int
    senior_count: int
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenditureCreate(BaseModel):
    annual_budget_id: uuid.UUID
    category: BudgetCategory
    item_name: str
    amount: int
    expense_date: date
    note: Optional[str] = None


class ExpenditureResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    annual_budget_id: uuid.UUID
    category: BudgetCategory
    item_name: str
    amount: int
    expense_date: date
    note: Optional[str]
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}

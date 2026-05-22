from __future__ import annotations
from typing import List

from pydantic import BaseModel, EmailStr, field_validator

from app.models.business_unit import BusinessUnitType


class RegisterRequest(BaseModel):
    # 기관 정보
    tenant_name: str
    tenant_address: str
    business_types: List[BusinessUnitType]

    # 관리자 계정
    admin_name: str
    admin_email: EmailStr
    admin_password: str

    @field_validator("business_types")
    @classmethod
    def at_least_one_type(cls, v: List[BusinessUnitType]) -> List[BusinessUnitType]:
        if not v:
            raise ValueError("사업 유형을 최소 1개 선택해야 합니다.")
        return list(set(v))  # 중복 제거

    @field_validator("admin_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다.")
        return v

    @field_validator("tenant_name", "tenant_address", "admin_name")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("필수 항목입니다.")
        return v.strip()


class RegisterResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    admin_email: str
    message: str

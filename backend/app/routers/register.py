from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password
from app.models.business_unit import BusinessUnitType
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.business_unit import TYPE_DEFAULTS
from app.models.business_unit import BusinessUnit
from app.schemas.register import RegisterRequest, RegisterResponse

router = APIRouter(prefix="/register", tags=["register"])

_TYPE_NAMES = {
    BusinessUnitType.PUBLIC_BENEFIT:  "공익활동형",
    BusinessUnitType.SOCIAL_SERVICE:  "사회서비스형",
    BusinessUnitType.MARKET:          "시장형",
}


@router.post("", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    [기관 최초 등록] 기관(테넌트) + 사업단 + 관리자 계정을 한 번에 생성.
    선택한 사업 유형(공익활동형·사회서비스형·시장형)별 사업단이 자동 생성됨.
    인증 불필요 (온보딩 화면에서 호출).

    Args:
        data.tenant_name     (str)              : 기관명. 중복 불가. 예) "서울노인일자리센터"
        data.tenant_address  (str)              : 기관 주소.
        data.business_types  (List[str])        : 사업 유형 목록. 최소 1개 필수.
                                                  "public_benefit" | "social_service" | "market"
        data.admin_name      (str)              : 관리자 이름.
        data.admin_email     (str)              : 관리자 이메일. 중복 불가.
        data.admin_password  (str)              : 관리자 비밀번호. 8자 이상 필수.

    Returns:
        tenant_id   (str) : 생성된 기관 UUID.
        tenant_name (str) : 기관명.
        admin_email (str) : 관리자 이메일.
        message     (str) : 안내 메시지 (사업비 등록 유도).

    Raises:
        409 : admin_email 또는 tenant_name 중복
        422 : business_types 빈 배열, 비밀번호 8자 미만, 필수 항목 공백
    """
    # 이메일 중복 확인
    existing = await db.execute(select(User).where(User.email == data.admin_email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다.",
        )

    # 기관명 중복 확인
    dup = await db.execute(select(Tenant).where(Tenant.name == data.tenant_name))
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 기관명입니다.",
        )

    # 테넌트 생성
    tenant_code = f"T{uuid.uuid4().hex[:8].upper()}"
    tenant = Tenant(
        tenant_code=tenant_code,
        name=data.tenant_name,
        address=data.tenant_address,
        subscription_plan="basic",
        is_active=True,
    )
    db.add(tenant)
    await db.flush()

    # 사업단 생성 (선택한 유형마다)
    current_year = __import__("datetime").date.today().year
    for btype in data.business_types:
        if btype != BusinessUnitType.MARKET:
            defaults = TYPE_DEFAULTS[btype.value]
            bu = BusinessUnit(
                tenant_id=tenant.id,
                name=_TYPE_NAMES[btype],
                type=btype,
                year=current_year,
                **defaults,
            )
        else:
            bu = BusinessUnit(
                tenant_id=tenant.id,
                name=_TYPE_NAMES[btype],
                type=btype,
                year=current_year,
                monthly_default_hours=60,
                monthly_max_hours=60,
                total_annual_hours=660,
                session_default_hours=3,
                session_max_hours=8,
                carry_over_enabled=False,
            )
        db.add(bu)

    # 관리자 계정 생성
    admin = User(
        tenant_id=tenant.id,
        name=data.admin_name,
        email=data.admin_email,
        password_hash=hash_password(data.admin_password),
        role=UserRole.TENANT_ADMIN,
        is_active=True,
    )
    db.add(admin)
    await db.commit()

    return RegisterResponse(
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        admin_email=admin.email,
        message="기관 등록이 완료되었습니다. 로그인 후 사업비를 등록해주세요.",
    )

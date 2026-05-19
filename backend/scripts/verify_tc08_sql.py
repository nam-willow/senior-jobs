"""
TC-08 검증: deleted_at IS NULL 필터가 실제 SQL WHERE 절에 포함되는지 확인.

실행: cd backend && python scripts/verify_tc08_sql.py
"""
import logging
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# SQLAlchemy SQL 로그 활성화
logging.basicConfig(format="%(message)s", level=logging.WARNING)
sql_logger = logging.getLogger("sqlalchemy.engine")
sql_logger.setLevel(logging.INFO)

SYNC_URL = "postgresql+psycopg2://senior_jobs_user:changeme@localhost:5432/senior_jobs"
engine = create_engine(SYNC_URL, echo=False)  # echo는 logger로 제어

TENANT_ID = uuid.UUID("bd129bf5-970a-4d0c-aeaf-4f65c219f273")
USER_ID   = uuid.UUID("8700f9e5-c8f0-4504-ab09-c2f210578396")
SENIOR_ID = uuid.uuid4()

INSERT_SQL = text("""
INSERT INTO monthly_work_records
  (id, tenant_id, senior_id, year, month,
   worked_hours, worked_days, amount_paid, status, created_by,
   created_at, deleted_at)
VALUES
  -- 정상 기록: 5월 30h
  (:id1, :tid, :sid, 2025, 5, 30, 10, 0, 'DRAFT', :uid, NOW(), NULL),
  -- Soft Delete 기록: 6월 30h (deleted_at 있음 → 합산 제외되어야 함)
  (:id2, :tid, :sid, 2025, 6, 30, 10, 0, 'DRAFT', :uid, NOW(), :deleted_at)
""")

from app.services.work_hours import calculate_monthly_rows

with Session(engine) as session:
    session.begin()
    session.execute(text("SET LOCAL app.current_tenant = 'ALL'"))
    # FK 체크 우회 (검증 전용 스크립트, rollback으로 정리)
    session.execute(text("SET LOCAL session_replication_role = replica"))

    session.execute(INSERT_SQL, {
        "id1": uuid.uuid4(), "id2": uuid.uuid4(),
        "tid": TENANT_ID, "sid": SENIOR_ID, "uid": USER_ID,
        "deleted_at": datetime.now(timezone.utc),
    })

    print("=" * 60)
    print("▶ calculate_monthly_rows 실행 (month=7, 실제 DB 쿼리)")
    print("  삽입 데이터: 5월 30h(정상) + 6월 30h(soft-deleted)")
    print("  기대: worked_so_far = 30h (deleted 제외), 결과 11행")
    print("=" * 60)

    # SQL 로그 ON
    sql_logger.setLevel(logging.INFO)

    result = calculate_monthly_rows(
        db=session,
        senior_id=str(SENIOR_ID),
        year=2025,
        month=7,
        business_unit_type="public_benefit",
        monthly_default_hours=30,
        monthly_max_hours=42,
        total_allocated_hours=330,
        session_hours=3,
        carry_over_enabled=True,
    )

    sql_logger.setLevel(logging.WARNING)
    print("=" * 60)
    print(f"▶ 결과: {result}행")
    # worked_so_far=30, remaining=300, 5개월, ideal=60h/3h=20행
    # allowed_max=min(10+1,14)=11 → min(20,11)=11
    print(f"  기대: 11행  {'✅ PASS' if result == 11 else '❌ FAIL'}")
    print("=" * 60)

    session.rollback()  # 테스트 데이터 롤백
    print("▶ 테스트 데이터 롤백 완료 (DB 오염 없음)")

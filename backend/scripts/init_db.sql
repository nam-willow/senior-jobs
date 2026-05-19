-- PostgreSQL 초기화 스크립트
-- gen_random_uuid() 사용을 위한 pgcrypto 확장
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- RLS 전용 설정 함수
-- app.current_tenant 미설정 시 빈 문자열 대신 오류 방지
ALTER DATABASE senior_jobs SET app.current_tenant = '';

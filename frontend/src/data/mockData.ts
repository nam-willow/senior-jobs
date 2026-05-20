import type { Senior, Budget, Alert, TabType } from '../types';

export const fmt = (n: number) => Number(n).toLocaleString('ko-KR');
export const won = (n: number) => fmt(n) + '원';

export const TABS: TabType[] = ['공익활동형', '사회서비스형', '시장형'];

export const TAB_TONE: Record<TabType, { color: string; chip: string }> = {
  '공익활동형':   { color: 'var(--green-700)', chip: 'green' },
  '사회서비스형': { color: 'var(--info)',       chip: 'info'  },
  '시장형':       { color: 'var(--warm)',       chip: 'warm'  },
};

export const BUDGET: Record<TabType, Budget> = {
  '공익활동형': {
    color: 'var(--green-700)', count: 120, pct: 66,
    total: 14400000, used: 9600000, remain: 4800000,
    lines: [
      { l: '어르신 임금', pct: 78,  used: 8580000,  total: 11000000 },
      { l: '담당자 임금', pct: 100, used: 2400000,  total: 2400000  },
      { l: '사업진행비', pct: 52,  used: 520000,   total: 1000000  },
    ],
  },
  '사회서비스형': {
    color: 'var(--info)', count: 85, pct: 82,
    total: 22000000, used: 18040000, remain: 3960000,
    lines: [
      { l: '어르신 임금', pct: 85, used: 15300000, total: 18000000 },
      { l: '담당자 임금', pct: 91, used: 3640000,  total: 4000000  },
      { l: '사업진행비', pct: 0,  used: 0,        total: 0        },
    ],
  },
  '시장형': {
    color: 'var(--warm)', count: 42, pct: 45,
    total: 8000000, used: 3600000, remain: 4400000,
    lines: [
      { l: '어르신 임금', pct: 45, used: 2700000, total: 6000000 },
      { l: '담당자 임금', pct: 50, used: 1000000, total: 2000000 },
      { l: '사업진행비', pct: 0,  used: 0,       total: 0       },
    ],
  },
};

export const SENIORS: Senior[] = [
  { id: 1,  name: '김영자', birth: '1948.03.15', phone: '010-2345-XXXX', unit: '공익활동형',   wp: '강남구 보건소',     totalH: 150, remainH: 180, paid: 450000, consults: 4, status: '정상',   sw: '김복지', note: '건강 상태 양호. 근무 의지 높음.' },
  { id: 2,  name: '박철수', birth: '1950.07.22', phone: '010-3456-XXXX', unit: '공익활동형',   wp: '서초구 도서관',     totalH: 314, remainH: 16,  paid: 942000, consults: 2, status: '임박',   sw: '이사복', note: '연간 시간 소진 임박. 6월부터 휴식 권고.' },
  { id: 3,  name: '이순희', birth: '1945.11.30', phone: '010-4567-XXXX', unit: '공익활동형',   wp: '강남구 보건소',     totalH: 90,  remainH: 240, paid: 270000, consults: 0, status: '미상담', sw: '김복지', note: '지난 상담 없음. 다음 주 방문 예정.' },
  { id: 4,  name: '최대호', birth: '1952.04.05', phone: '010-5678-XXXX', unit: '사회서비스형', wp: '송파구 어린이집',   totalH: 180, remainH: 150, paid: 540000, consults: 6, status: '정상',   sw: '김복지', note: '' },
  { id: 5,  name: '정미숙', birth: '1949.09.18', phone: '010-6789-XXXX', unit: '사회서비스형', wp: '강동구 복지관',     totalH: 270, remainH: 60,  paid: 810000, consults: 3, status: '정상',   sw: '이사복', note: '' },
  { id: 6,  name: '한상호', birth: '1946.12.01', phone: '010-7890-XXXX', unit: '공익활동형',   wp: '광진구 보건소',     totalH: 120, remainH: 210, paid: 360000, consults: 1, status: '정상',   sw: '김복지', note: '' },
  { id: 7,  name: '윤정숙', birth: '1953.02.14', phone: '010-8901-XXXX', unit: '공익활동형',   wp: '성동구 도서관',     totalH: 60,  remainH: 270, paid: 180000, consults: 5, status: '정상',   sw: '김복지', note: '' },
  { id: 8,  name: '강민준', birth: '1951.06.28', phone: '010-9012-XXXX', unit: '시장형',       wp: '마포구 카페사업단', totalH: 200, remainH: 130, paid: 600000, consults: 2, status: '정상',   sw: '이사복', note: '' },
  { id: 9,  name: '박영순', birth: '1944.08.10', phone: '010-1234-XXXX', unit: '공익활동형',   wp: '강남구 환경지킴이', totalH: 90,  remainH: 240, paid: 270000, consults: 0, status: '미상담', sw: '김복지', note: '35일째 상담 없음. 긴급 방문 필요.' },
  { id: 10, name: '장순자', birth: '1947.05.23', phone: '010-2222-XXXX', unit: '사회서비스형', wp: '강동구 복지관',     totalH: 240, remainH: 90,  paid: 720000, consults: 2, status: '정상',   sw: '이사복', note: '' },
  { id: 11, name: '오영자', birth: '1950.01.07', phone: '010-3333-XXXX', unit: '시장형',       wp: '마포구 카페사업단', totalH: 160, remainH: 170, paid: 480000, consults: 1, status: '정상',   sw: '김복지', note: '' },
  { id: 12, name: '신복례', birth: '1948.10.19', phone: '010-4444-XXXX', unit: '공익활동형',   wp: '강남구 보건소',     totalH: 100, remainH: 230, paid: 300000, consults: 3, status: '정상',   sw: '김복지', note: '' },
];

export const ALERTS: Alert[] = [
  { id: 'a1', tone: 'danger', title: '박영순 어르신 35일째 상담 없음',  meta: '공익활동형 · 강남구',   t: '오늘 09:14', goto: 'consult',   seniorId: 9 },
  { id: 'a2', tone: 'warm',   title: '사회서비스형 잔액 9.8% 남음',     meta: '사업진행비 점검 필요',   t: '어제 16:02', goto: 'budget',    tab: '사회서비스형' },
  { id: 'a3', tone: 'gold',   title: '박철수 어르신 연간시간 96% 소진', meta: '잔여 16시간 / 330시간', t: '3일 전',     goto: 'seniors',   seniorId: 2 },
  { id: 'a4', tone: 'info',   title: '근무기록 12건 결재 대기',          meta: '월별 근무 등록 → 결재',  t: '5일 전',     goto: 'approvals' },
];

export const MONTHLY = [
  { m: '1월', pub: 900,  svc: 600, mkt: 380 },
  { m: '2월', pub: 840,  svc: 600, mkt: 420 },
  { m: '3월', pub: 960,  svc: 620, mkt: 560 },
  { m: '4월', pub: 900,  svc: 600, mkt: 480 },
  { m: '5월', pub: 1050, svc: 640, mkt: 620 },
  { m: '6월', pub: 870,  svc: 600, mkt: 450 },
];

export const ORGS = [
  { name: '강남종합사회복지관', area: '서울 강남구', type: '공익활동형',   n: 120, hrs: 1050, exec: 66, state: '정상' },
  { name: '서초시니어플라자',   area: '서울 서초구', type: '사회서비스형', n: 85,  hrs: 640,  exec: 82, state: '정상' },
  { name: '송파은빛마을',       area: '서울 송파구', type: '시장형',       n: 42,  hrs: 620,  exec: 45, state: '확인필요' },
  { name: '강동노인종합복지관', area: '서울 강동구', type: '공익활동형',   n: 64,  hrs: 480,  exec: 71, state: '정상' },
  { name: '광진은빛일터',       area: '서울 광진구', type: '사회서비스형', n: 38,  hrs: 310,  exec: 58, state: '정상' },
];

export type TabType = '공익활동형' | '사회서비스형' | '시장형';
export type PageType =
  | 'dashboard' | 'seniors' | 'work' | 'worklog'
  | 'salary' | 'consult' | 'budget' | 'approvals' | 'alerts';

export interface Senior {
  id: number;
  name: string;
  birth: string;
  phone: string;
  unit: TabType;
  wp: string;
  totalH: number;
  remainH: number;
  paid: number;
  consults: number;
  status: '정상' | '임박' | '미상담';
  sw: string;
  note: string;
}

export interface BudgetLine {
  l: string;
  pct: number;
  used: number;
  total: number;
}

export interface Budget {
  color: string;
  count: number;
  pct: number;
  total: number;
  used: number;
  remain: number;
  lines: BudgetLine[];
}

export interface Alert {
  id: string;
  tone: 'danger' | 'warm' | 'gold' | 'info';
  title: string;
  meta: string;
  t: string;
  goto?: PageType;
  tab?: TabType;
  seniorId?: number;
}

export interface NavItem {
  id: PageType;
  label: string;
  badgeKey?: 'approvals' | 'alerts';
}

export type ChipTone = 'green' | 'info' | 'warm' | 'gold' | 'danger' | 'neutral';
export type ButtonVariant = 'primary' | 'secondary' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

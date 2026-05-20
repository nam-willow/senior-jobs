import type { ReactNode } from 'react';
import type { PageType, TabType } from '../../types';
import { Logo } from '../shared/Logo';
import { Icons } from '../shared/Icons';
import { ALERTS } from '../../data/mockData';

const NAV_ITEMS = [
  { id: 'dashboard' as PageType,  ic: Icons.grid,      label: '메인 대시보드' },
  { id: 'seniors'   as PageType,  ic: Icons.people,    label: '어르신 목록' },
  { id: 'work'      as PageType,  ic: Icons.briefcase, label: '월별 근무 등록' },
  { id: 'worklog'   as PageType,  ic: Icons.doc,       label: '근무일지 출력' },
  { id: 'salary'    as PageType,  ic: Icons.coin,      label: '급여대장' },
  { id: 'consult'   as PageType,  ic: Icons.heart,     label: '상담일지' },
  { id: 'budget'    as PageType,  ic: Icons.chart,     label: '사업비 관리' },
  { id: 'approvals' as PageType,  ic: Icons.check,     label: '결재 처리',  badge: 12 },
  { id: 'alerts'    as PageType,  ic: Icons.bell,      label: '자동 알림',  badge: ALERTS.length },
];

interface AdminShellProps {
  page: PageType;
  tab?: TabType;
  year: number;
  month: number;
  onNavigate: (page: PageType) => void;
  children: ReactNode;
}

export function AdminShell({ page, year, month, onNavigate, children }: AdminShellProps) {
  const pageLabel = NAV_ITEMS.find((n) => n.id === page)?.label || '';

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--cream-50)' }}>
      {/* SIDEBAR */}
      <aside className="sb" style={{
        width: 260, background: '#fff', borderRight: '1px solid var(--line)',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
        position: 'sticky', top: 0, height: '100vh',
      }}>
        <div style={{ padding: '24px 24px 18px', borderBottom: '1px solid var(--line-soft)', cursor: 'pointer' }}
             onClick={() => onNavigate('dashboard')}>
          <Logo/>
        </div>

        {/* user card */}
        <div style={{ padding: '16px 20px' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12,
            background: 'var(--green-50)', border: '1px solid var(--green-200)',
            borderRadius: 14, padding: '12px 14px',
          }}>
            <div style={{
              width: 44, height: 44, borderRadius: '50%',
              background: 'var(--green-700)', color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 18, fontWeight: 700,
            }}>김</div>
            <div style={{ lineHeight: 1.2 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink-900)' }}>김복지 사회복지사</div>
              <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 2 }}>강남종합사회복지관</div>
            </div>
          </div>
        </div>

        <nav style={{ padding: '4px 12px', flex: 1, display: 'flex', flexDirection: 'column', gap: 2, overflowY: 'auto' }}>
          {NAV_ITEMS.map((n) => {
            const active = page === n.id;
            return (
              <div key={n.id} onClick={() => onNavigate(n.id)} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '13px 14px', borderRadius: 12, cursor: 'pointer',
                background: active ? 'var(--green-700)' : 'transparent',
                color: active ? '#fff' : 'var(--ink-700)',
                fontWeight: active ? 700 : 500, fontSize: 16,
                transition: 'background 0.15s',
              }}>
                <span style={{ display: 'flex' }}><n.ic/></span>
                <span style={{ flex: 1 }}>{n.label}</span>
                {n.badge != null && n.badge > 0 && (
                  <span style={{
                    background: active ? 'rgba(255,255,255,0.2)' : 'var(--warm-soft)',
                    color: active ? '#fff' : '#9B4221',
                    borderRadius: 999, padding: '2px 10px', fontSize: 12, fontWeight: 700,
                  }}>{n.badge}</span>
                )}
              </div>
            );
          })}
        </nav>

        <div style={{ padding: '16px 20px', borderTop: '1px solid var(--line-soft)', fontSize: 13, color: 'var(--ink-500)' }}>
          2026 회계연도 · <span style={{ color: 'var(--green-700)', fontWeight: 700 }}>11월</span>까지
        </div>
      </aside>

      {/* MAIN */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Topbar */}
        <header style={{
          height: 76, background: '#fff', borderBottom: '1px solid var(--line)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 32px', flexShrink: 0, position: 'sticky', top: 0, zIndex: 10,
        }}>
          <div>
            <div style={{ fontSize: 13, color: 'var(--ink-500)', marginBottom: 2 }}>
              {pageLabel} · <span style={{ color: 'var(--green-700)' }}>{year}년 {month}월</span>
            </div>
            <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--ink-900)' }}>
              {page === 'dashboard' ? '안녕하세요, 김복지 선생님 👋' : pageLabel}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '10px 14px', border: '1.5px solid var(--line)',
              borderRadius: 12, color: 'var(--ink-700)', fontSize: 15, fontWeight: 600,
              background: '#fff', cursor: 'pointer',
            }}>
              <span>{year}년 {month}월</span>
              <Icons.arrow/>
            </div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '10px 16px', border: '1.5px solid var(--line)',
              borderRadius: 12, color: 'var(--ink-500)', fontSize: 15, minWidth: 220,
              background: '#fff',
            }}>
              <Icons.search/> <span>어르신·기관 검색…</span>
            </div>
            <button onClick={() => onNavigate('alerts')} style={{
              width: 48, height: 48, borderRadius: 12, border: '1.5px solid var(--line)',
              background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
              position: 'relative', color: 'var(--ink-700)', cursor: 'pointer',
            }}>
              <Icons.bell/>
              <span style={{
                position: 'absolute', top: 6, right: 6, minWidth: 18, height: 18, padding: '0 4px',
                background: 'var(--warm)', color: '#fff', borderRadius: '50%',
                fontSize: 10, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center',
                border: '2px solid #fff',
              }}>{ALERTS.length}</span>
            </button>
          </div>
        </header>

        <main className="content" style={{ flex: 1, padding: '28px 32px 32px', minWidth: 0 }}>
          {children}
        </main>
      </div>
    </div>
  );
}

import { useState, type ReactNode } from 'react';
import type { PageType, TabType } from '../../types';
import { Logo } from '../shared/Logo';
import { Icons } from '../shared/Icons';
import { useAuthStore } from '../../stores/authStore';
import { useAlerts } from '../../hooks/useAlerts';
import { useAppStore } from '../../stores/appStore';

const NAV_ITEMS = [
  { id: 'dashboard' as PageType,  ic: Icons.grid,      label: '메인 대시보드' },
  { id: 'seniors'   as PageType,  ic: Icons.people,    label: '어르신 목록' },
  { id: 'work'      as PageType,  ic: Icons.briefcase, label: '월별 근무 등록' },
  { id: 'worklog'   as PageType,  ic: Icons.doc,       label: '근무일지 출력' },
  { id: 'salary'    as PageType,  ic: Icons.coin,      label: '급여대장' },
  { id: 'consult'   as PageType,  ic: Icons.heart,     label: '상담일지' },
  { id: 'budget'    as PageType,  ic: Icons.chart,     label: '사업비 관리' },
  { id: 'approvals' as PageType,  ic: Icons.check,     label: '결재 처리' },
  { id: 'alerts'    as PageType,  ic: Icons.bell,      label: '자동 알림' },
  { id: 'settings'  as PageType,  ic: Icons.search,    label: '관리자 설정' },
];

interface AdminShellProps {
  page: PageType;
  tab?: TabType;
  year: number;
  month: number;
  onNavigate: (page: PageType) => void;
  onYearMonthChange: (year: number, month: number) => void;
  children: ReactNode;
}

export function AdminShell({ page, year, month, onNavigate, onYearMonthChange, children }: AdminShellProps) {
  const pageLabel = NAV_ITEMS.find((n) => n.id === page)?.label || '';
  const logout = useAuthStore((s) => s.logout);
  const userInfo = useAuthStore((s) => s.userInfo);
  const storeYear = useAppStore((s) => s.year);
  const { alerts } = useAlerts(storeYear);

  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerYear, setPickerYear] = useState(year);
  const [pickerMonth, setPickerMonth] = useState(month);

  const applyPicker = () => {
    onYearMonthChange(pickerYear, pickerMonth);
    setPickerOpen(false);
  };

  const displayName = userInfo?.name || '—';
  const displayOrg = userInfo?.tenant_name || '';
  const displayInitial = displayName.charAt(0) || '?';
  const alertCount = alerts.length;

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
            }}>{displayInitial}</div>
            <div style={{ lineHeight: 1.2 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink-900)' }}>{displayName}</div>
              <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 2 }}>{displayOrg}</div>
            </div>
          </div>
        </div>

        <nav style={{ padding: '4px 12px', flex: 1, display: 'flex', flexDirection: 'column', gap: 2, overflowY: 'auto' }}>
          {NAV_ITEMS.map((n) => {
            const active = page === n.id;
            const badge = n.id === 'alerts' ? alertCount : 0;
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
                {badge > 0 && (
                  <span style={{
                    background: active ? 'rgba(255,255,255,0.2)' : 'var(--warm-soft)',
                    color: active ? '#fff' : '#9B4221',
                    borderRadius: 999, padding: '2px 10px', fontSize: 12, fontWeight: 700,
                  }}>{badge}</span>
                )}
              </div>
            );
          })}
        </nav>

        <div style={{ padding: '16px 20px', borderTop: '1px solid var(--line-soft)', fontSize: 13, color: 'var(--ink-500)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{year}년 회계연도</span>
          <span onClick={() => logout()} style={{ cursor: 'pointer', color: 'var(--ink-400)', fontWeight: 500 }}>로그아웃</span>
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
              {page === 'dashboard' ? `안녕하세요, ${displayName} 선생님 👋` : pageLabel}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* Year/Month picker button */}
            <div onClick={() => { setPickerYear(year); setPickerMonth(month); setPickerOpen(true); }} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '10px 14px', border: '1.5px solid var(--line)',
              borderRadius: 12, color: 'var(--ink-700)', fontSize: 15, fontWeight: 600,
              background: '#fff', cursor: 'pointer',
            }}>
              <span>{year}년 {month}월</span>
              <Icons.arrow/>
            </div>
            <button onClick={() => onNavigate('alerts')} style={{
              width: 48, height: 48, borderRadius: 12, border: '1.5px solid var(--line)',
              background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
              position: 'relative', color: 'var(--ink-700)', cursor: 'pointer',
            }}>
              <Icons.bell/>
              {alertCount > 0 && (
                <span style={{
                  position: 'absolute', top: 6, right: 6, minWidth: 18, height: 18, padding: '0 4px',
                  background: 'var(--warm)', color: '#fff', borderRadius: '50%',
                  fontSize: 10, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  border: '2px solid #fff',
                }}>{alertCount}</span>
              )}
            </button>
          </div>
        </header>

        <main className="content" style={{ flex: 1, padding: '28px 32px 32px', minWidth: 0 }}>
          {children}
        </main>
      </div>

      {/* Mobile bottom nav */}
      <nav className="mobile-nav">
        {[
          { id: 'dashboard' as PageType, label: '홈',     ic: Icons.grid    },
          { id: 'seniors'   as PageType, label: '어르신', ic: Icons.people  },
          { id: 'work'      as PageType, label: '근무',   ic: Icons.briefcase },
          { id: 'consult'   as PageType, label: '상담',   ic: Icons.heart   },
          { id: 'alerts'    as PageType, label: '알림',   ic: Icons.bell    },
        ].map((n) => (
          <button key={n.id} className={`mobile-nav-item${page === n.id ? ' active' : ''}`} onClick={() => onNavigate(n.id)}>
            <n.ic/>
            <span>{n.label}</span>
          </button>
        ))}
      </nav>

      {/* Year/Month picker modal */}
      {pickerOpen && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200,
        }} onClick={() => setPickerOpen(false)}>
          <div onClick={(e) => e.stopPropagation()} style={{
            background: '#fff', borderRadius: 20, padding: '28px 32px', width: 340,
            boxShadow: '0 8px 40px rgba(0,0,0,0.18)',
          }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--ink-900)', marginBottom: 20 }}>연도 · 월 선택</div>

            <div style={{ marginBottom: 18 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-500)', marginBottom: 8 }}>연도</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {[2024, 2025, 2026, 2027].map((y) => (
                  <div key={y} onClick={() => setPickerYear(y)} style={{
                    padding: '8px 16px', borderRadius: 10, cursor: 'pointer', fontSize: 15, fontWeight: 600,
                    background: pickerYear === y ? 'var(--green-700)' : 'var(--cream-50)',
                    color: pickerYear === y ? '#fff' : 'var(--ink-700)',
                    border: `1.5px solid ${pickerYear === y ? 'var(--green-700)' : 'var(--line)'}`,
                  }}>{y}년</div>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-500)', marginBottom: 8 }}>월</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                  <div key={m} onClick={() => setPickerMonth(m)} style={{
                    padding: '10px 0', borderRadius: 10, cursor: 'pointer', fontSize: 15, fontWeight: 600,
                    textAlign: 'center',
                    background: pickerMonth === m ? 'var(--green-700)' : 'var(--cream-50)',
                    color: pickerMonth === m ? '#fff' : 'var(--ink-700)',
                    border: `1.5px solid ${pickerMonth === m ? 'var(--green-700)' : 'var(--line)'}`,
                  }}>{m}월</div>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setPickerOpen(false)} style={{
                flex: 1, padding: '12px 0', borderRadius: 12, border: '1.5px solid var(--line)',
                background: '#fff', fontSize: 15, fontWeight: 600, cursor: 'pointer', color: 'var(--ink-700)',
              }}>취소</button>
              <button onClick={applyPicker} style={{
                flex: 2, padding: '12px 0', borderRadius: 12, border: 'none',
                background: 'var(--green-700)', fontSize: 15, fontWeight: 700, cursor: 'pointer', color: '#fff',
              }}>적용</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

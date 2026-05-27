import { useState } from 'react';
import type { PageType, TabType } from '../types';
import { useAppStore } from '../stores/appStore';
import { useAlerts } from '../hooks/useAlerts';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Button } from '../components/shared/Button';
import { Icons } from '../components/shared/Icons';

const TYPES = ['전체', '긴급', '예산', '어르신', '결재', '시스템'];
const typeMap: Record<string, string> = { danger: '긴급', warm: '예산', gold: '어르신', info: '결재' };

const toneStyle: Record<string, { dot: string; chip: string }> = {
  danger: { dot: 'var(--danger)', chip: 'danger' },
  warm:   { dot: 'var(--warm)',   chip: 'warm'   },
  gold:   { dot: 'var(--gold)',   chip: 'gold'   },
  info:   { dot: 'var(--info)',   chip: 'info'   },
};

interface AlertsProps {
  onNavigate: (page: PageType, tab?: TabType, seniorId?: number) => void;
}

export function Alerts({ onNavigate }: AlertsProps) {
  const year = useAppStore((s) => s.year);
  const { alerts, loading } = useAlerts(year);
  const [filter, setFilter] = useState('전체');
  const [readSet, setReadSet] = useState<Set<string>>(new Set());

  const filtered = alerts.filter((a) => {
    if (filter === '전체') return true;
    if (filter === '시스템') return !typeMap[a.tone];
    return typeMap[a.tone] === filter;
  });

  const handleClick = (a: typeof alerts[0]) => {
    setReadSet((p) => new Set(p).add(a.id));
    if (a.goto) onNavigate(a.goto as PageType, a.tab as TabType | undefined);
  };

  const urgentCount  = alerts.filter((a) => a.tone === 'danger').length;
  const unreadCount  = alerts.length - readSet.size;
  const todayCount   = 0; // 백엔드가 타임스탬프를 주지 않으므로 생략

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {TYPES.map((t) => (
            <div key={t} onClick={() => setFilter(t)} style={{
              padding: '10px 16px', borderRadius: 999, fontSize: 14, fontWeight: 600, cursor: 'pointer',
              background: filter === t ? 'var(--green-700)' : '#fff',
              color:      filter === t ? '#fff' : 'var(--ink-700)',
              border:     `1.5px solid ${filter === t ? 'var(--green-700)' : 'var(--line)'}`,
            }}>{t}</div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="ghost" size="sm" onClick={() => setReadSet(new Set(alerts.map((a) => a.id)))}>모두 읽음 처리</Button>
          <Button variant="secondary" size="sm" icon={<Icons.gear/>}>알림 설정</Button>
        </div>
      </div>

      <div className="g4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 22 }}>
        {[
          { lb: '전체 알림', val: alerts.length,  color: 'var(--ink-900)'   },
          { lb: '긴급',      val: urgentCount,     color: 'var(--danger)'    },
          { lb: '안 읽음',   val: unreadCount,     color: 'var(--warm)'      },
          { lb: '오늘',      val: todayCount,      color: 'var(--green-700)' },
        ].map((s) => (
          <div key={s.lb} style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 18, padding: '16px 20px', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>{s.lb}</div>
            <div className="num" style={{ fontSize: 28, fontWeight: 800, color: s.color, marginTop: 4 }}>
              {s.val}<span style={{ fontSize: 14, color: 'var(--ink-500)', marginLeft: 4 }}>건</span>
            </div>
          </div>
        ))}
      </div>

      <Card padding="0">
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {loading && (
            <div style={{ padding: 48, textAlign: 'center', color: 'var(--ink-400)' }}>로딩 중…</div>
          )}
          {!loading && filtered.length === 0 && (
            <div style={{ padding: 48, textAlign: 'center', color: 'var(--ink-400)' }}>해당 알림이 없습니다.</div>
          )}
          {!loading && filtered.map((a, i) => {
            const t = toneStyle[a.tone] ?? { dot: 'var(--ink-400)', chip: 'neutral' };
            const read = readSet.has(a.id);
            return (
              <div key={a.id} onClick={() => handleClick(a)} style={{
                display: 'flex', gap: 16, padding: '18px 24px',
                borderTop: i === 0 ? 'none' : '1px solid var(--line-soft)',
                cursor: 'pointer', background: read ? '#fff' : '#FCFBF7',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--cream-50)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = read ? '#fff' : '#FCFBF7')}
              >
                <div style={{ width: 12, height: 12, borderRadius: '50%', background: read ? 'transparent' : t.dot, border: read ? '2px solid var(--line)' : 'none', marginTop: 6, flexShrink: 0 }}/>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <Chip tone={t.chip as 'danger'|'warm'|'gold'|'info'|'neutral'} size="sm">
                      {typeMap[a.tone] ?? '시스템'}
                    </Chip>
                  </div>
                  <div style={{ fontSize: 17, fontWeight: read ? 600 : 800, color: 'var(--ink-900)', lineHeight: 1.4 }}>{a.title}</div>
                  <div style={{ fontSize: 14, color: 'var(--ink-500)', marginTop: 4 }}>{a.meta}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', color: 'var(--ink-400)' }}>
                  <Icons.arrow/>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <div style={{ marginTop: 12, fontSize: 12, color: 'var(--ink-500)', textAlign: 'center' }}>
        알림 클릭 시 해당 화면으로 자동 이동합니다 · 30일 이상된 알림은 자동 보관됩니다
      </div>
    </>
  );
}

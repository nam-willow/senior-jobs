import { useState } from 'react';
import type { PageType, TabType } from '../types';
import { ALERTS } from '../data/mockData';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Button } from '../components/shared/Button';
import { Icons } from '../components/shared/Icons';

const ALL_ALERTS = [
  ...ALERTS,
  { id: 'a5', tone: 'gold'  as const, title: '최대호 어르신 다음달 시간 초과 예상', meta: '사회서비스형 · 누적 추세 기반',  t: '5일 전', goto: 'seniors'  as PageType, tab: '사회서비스형' as TabType, seniorId: 4 },
  { id: 'a6', tone: 'info'  as const, title: '5월 급여대장 결재 승인 완료',          meta: '공익활동형 12건',               t: '1주 전', goto: 'salary'   as PageType },
  { id: 'a7', tone: 'warm'  as const, title: '공익활동형 사업진행비 48% 잔여',       meta: '예산 모니터링',                  t: '1주 전', goto: 'budget'   as PageType, tab: '공익활동형' as TabType },
  { id: 'a8', tone: 'info'  as const, title: '2026년도 2차 보조금 입금 확인',        meta: '보건복지부 · 5,400,000원',       t: '1주 전', goto: 'budget'   as PageType },
  { id: 'a9', tone: 'gold'  as const, title: '이순희 어르신 안전교육 미이수',        meta: '공익활동형 · 6/15까지 필수',     t: '2주 전', goto: 'seniors'  as PageType, tab: '공익활동형' as TabType, seniorId: 3 },
  { id: 'a10',tone: 'info'  as const, title: '월별 근무일지 양식 v2.1 적용',         meta: '시스템 공지',                    t: '2주 전', goto: 'worklog'  as PageType },
];

const TYPES = ['전체', '긴급', '예산', '어르신', '결재', '시스템'];
const typeMap: Record<string, string> = { danger: '긴급', warm: '예산', gold: '어르신', info: '결재' };

const toneStyle: Record<string, { bg: string; dot: string; chip: string }> = {
  danger: { bg: '#FBE3E3',          dot: 'var(--danger)', chip: 'danger' },
  warm:   { bg: 'var(--warm-soft)', dot: 'var(--warm)',   chip: 'warm'   },
  gold:   { bg: 'var(--gold-soft)', dot: 'var(--gold)',   chip: 'gold'   },
  info:   { bg: '#DFEBF1',          dot: 'var(--info)',   chip: 'info'   },
};

interface AlertsProps {
  onNavigate: (page: PageType, tab?: TabType, seniorId?: number) => void;
}

export function Alerts({ onNavigate }: AlertsProps) {
  const [filter, setFilter] = useState('전체');
  const [readSet, setReadSet] = useState<Set<string>>(new Set());

  const filtered = ALL_ALERTS.filter((a) => {
    if (filter === '전체') return true;
    if (filter === '시스템') return /시스템|양식|공지/.test(a.title);
    return typeMap[a.tone] === filter;
  });

  const handleClick = (a: typeof ALL_ALERTS[0]) => {
    setReadSet((p) => new Set(p).add(a.id));
    if (a.goto) onNavigate(a.goto, a.tab, a.seniorId);
  };

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
          <Button variant="ghost" size="sm" onClick={() => setReadSet(new Set(ALL_ALERTS.map((a) => a.id)))}>모두 읽음 처리</Button>
          <Button variant="secondary" size="sm" icon={<Icons.gear/>}>알림 설정</Button>
        </div>
      </div>

      <div className="g4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 22 }}>
        {[
          { lb: '전체 알림', val: ALL_ALERTS.length,                                    color: 'var(--ink-900)'  },
          { lb: '긴급',      val: ALL_ALERTS.filter(a => a.tone === 'danger').length,   color: 'var(--danger)'   },
          { lb: '안 읽음',   val: ALL_ALERTS.length - readSet.size,                     color: 'var(--warm)'     },
          { lb: '오늘',      val: ALL_ALERTS.filter(a => a.t.includes('오늘')).length, color: 'var(--green-700)' },
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
          {filtered.map((a, i) => {
            const t = toneStyle[a.tone];
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
                    <Chip tone={t.chip as 'danger'|'warm'|'gold'|'info'} size="sm">{typeMap[a.tone] || '시스템'}</Chip>
                    <span style={{ fontSize: 13, color: 'var(--ink-500)' }}>{a.t}</span>
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

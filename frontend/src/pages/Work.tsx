import { useState, useEffect, useRef } from 'react';
import type { TabType } from '../types';
import { SENIORS, fmt } from '../data/mockData';
import { UnitTabBar } from '../components/layout/UnitTabBar';
import { BudgetStrip } from '../components/layout/BudgetStrip';
import { AlertBox } from '../components/layout/AlertBox';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Button } from '../components/shared/Button';
import { Icons } from '../components/shared/Icons';

interface RowState { hours: string; amount: number; dirty: boolean; reason: string; }

interface WorkProps {
  tab: TabType;
  setTab: (t: TabType) => void;
  focusSenior: number | null;
  setFocusSenior: (id: number | null) => void;
}

const RATE = 4000;

export function Work({ tab, setTab, focusSenior, setFocusSenior }: WorkProps) {
  const tabSeniors = SENIORS.filter((s) => s.unit === tab);

  const makeInitial = () => {
    const obj: Record<number, RowState> = {};
    tabSeniors.forEach((s) => { obj[s.id] = { hours: '', amount: 0, dirty: false, reason: '' }; });
    return obj;
  };

  const [rows, setRows] = useState<Record<number, RowState>>(makeInitial);
  useEffect(() => { setRows(makeInitial()); }, [tab]);

  const focusRowRef = useRef<HTMLTableRowElement>(null);
  useEffect(() => {
    if (focusSenior && focusRowRef.current) {
      focusRowRef.current.scrollIntoView({ block: 'center' });
      const t = setTimeout(() => setFocusSenior(null), 2500);
      return () => clearTimeout(t);
    }
  }, [focusSenior]);

  const handleH = (id: number, raw: string) => {
    const v = raw.replace(/[^\d.]/g, '');
    const n = parseFloat(v) || 0;
    setRows((p) => ({ ...p, [id]: { ...p[id], hours: v, amount: v ? Math.round(n * RATE) : 0, dirty: true } }));
  };
  const handleReason = (id: number, r: string) => {
    setRows((p) => ({ ...p, [id]: { ...p[id], reason: r } }));
  };

  const dirtyCount  = Object.values(rows).filter((r) => r.dirty).length;
  const blockedCount = Object.values(rows).filter((r) => parseFloat(r.hours) > 43).length;
  const warnCount   = Object.values(rows).filter((r) => { const h = parseFloat(r.hours)||0; return h > 42 && h <= 43; }).length;

  return (
    <>
      <UnitTabBar tab={tab} onChange={setTab} right={
        <>
          <span style={{ fontSize: 14, color: 'var(--ink-500)' }}>수정 <strong className="num" style={{ color: dirtyCount > 0 ? 'var(--warm)' : 'var(--ink-700)' }}>{dirtyCount}</strong>건</span>
          <Button variant="secondary" size="sm" icon={<Icons.check/>}>결재 요청</Button>
          <Button variant="primary" size="sm" icon={<Icons.check/>}>전체 저장</Button>
        </>
      }/>

      <BudgetStrip tab={tab}/>

      <AlertBox tone="info">
        근무시간만 입력하면 지급금액이 자동 계산됩니다. 변경된 행은 <strong>노란색</strong>으로 표시되며, <strong>전체 저장</strong> 시 변경된 행만 일괄 저장됩니다.
      </AlertBox>

      {warnCount > 0 && (
        <AlertBox tone="warn">
          <strong>완충 구간</strong> ({warnCount}건): 월 42시간 초과 ~ 43시간 이하. 각 행에 초과 사유를 입력해야 저장됩니다.
        </AlertBox>
      )}
      {blockedCount > 0 && (
        <AlertBox tone="danger">
          <strong>저장 불가</strong> ({blockedCount}건): 43시간 초과. 시간을 조정해주세요.
        </AlertBox>
      )}

      <Card padding="0">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
          <thead>
            <tr style={{ background: 'var(--cream-50)' }}>
              {[['어르신 이름','left'],['근무장소','left'],['월 배정시간','center'],['남은 시간','center'],['남은 금액','right'],['근무시간 (h)','center'],['지급금액 (원)','right'],['상태','center']].map(([h, a]) => (
                <th key={h} style={{ padding: '14px 18px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, textAlign: a as 'left'|'center'|'right', whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tabSeniors.map((s) => {
              const r = rows[s.id] || { hours: '', amount: 0, dirty: false, reason: '' };
              const h = parseFloat(r.hours) || 0;
              const overWarn    = h > 42 && h <= 43;
              const overBlocked = h > 43;
              const focused     = focusSenior === s.id;
              return (
                <>
                  <tr key={s.id} ref={focused ? focusRowRef : null} style={{
                    borderTop: '1px solid var(--line-soft)',
                    background: focused    ? 'var(--green-50)'
                              : overBlocked ? '#FBE3E3'
                              : overWarn    ? '#FEF5E6'
                              : r.dirty    ? '#FFFBEB'
                              : '#fff',
                    outline:      focused ? '2px solid var(--green-600)' : 'none',
                    outlineOffset: -1,
                  }}>
                    <td style={{ padding: '14px 18px' }}>
                      <div style={{ fontSize: 17, fontWeight: 700, color: 'var(--ink-900)' }}>
                        {s.name}
                        {focused && <span style={{ fontSize: 12, color: 'var(--green-700)', marginLeft: 6 }}>◀ 선택됨</span>}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>{s.birth}</div>
                    </td>
                    <td style={{ padding: '14px 18px', color: 'var(--ink-700)' }}>{s.wp}</td>
                    <td style={{ padding: '14px 18px', textAlign: 'center', color: 'var(--ink-500)' }}>30h</td>
                    <td className="num" style={{ padding: '14px 18px', textAlign: 'center', color: s.remainH < 30 ? 'var(--danger)' : 'var(--green-700)', fontWeight: 700 }}>{s.remainH}h</td>
                    <td className="num" style={{ padding: '14px 18px', textAlign: 'right', color: 'var(--green-700)', fontWeight: 700 }}>{fmt(s.remainH * 30000)}원</td>
                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                      <input
                        value={r.hours}
                        onChange={(e) => handleH(s.id, e.target.value)}
                        placeholder="0"
                        style={{
                          width: 100, padding: '10px 12px',
                          border: `1.5px solid ${overBlocked ? 'var(--danger)' : overWarn ? 'var(--warm)' : 'var(--line)'}`,
                          borderRadius: 10, textAlign: 'center', fontSize: 16, fontWeight: 700,
                          outline: 'none',
                          background: overBlocked ? '#FBE3E3' : overWarn ? '#FEF5E6' : '#fff',
                          color: overBlocked ? 'var(--danger)' : 'var(--ink-900)',
                        }}
                      />
                    </td>
                    <td className="num" style={{ padding: '14px 18px', textAlign: 'right', color: r.amount ? 'var(--green-700)' : 'var(--ink-400)', fontWeight: r.amount ? 700 : 500, fontSize: 16 }}>
                      {r.amount ? fmt(r.amount) + '원' : '자동계산'}
                    </td>
                    <td style={{ padding: '14px 18px', textAlign: 'center' }}>
                      <Chip tone={overBlocked ? 'danger' : overWarn ? 'warm' : r.dirty ? 'gold' : 'neutral'} size="sm">
                        {overBlocked ? '저장불가' : overWarn ? '완충구간' : r.dirty ? '임시저장' : '미입력'}
                      </Chip>
                    </td>
                  </tr>
                  {overWarn && (
                    <tr key={`${s.id}-reason`} style={{ background: '#FEF5E6' }}>
                      <td colSpan={8} style={{ padding: '12px 18px 16px 36px', borderTop: '1px dashed var(--warm)' }}>
                        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                          <span style={{ fontSize: 13, color: 'var(--warm)', fontWeight: 700 }}>⚠️ 초과 사유 (필수):</span>
                          <input
                            value={r.reason}
                            onChange={(e) => handleReason(s.id, e.target.value)}
                            placeholder="예: 행사 지원으로 인한 추가 근무"
                            style={{ flex: 1, padding: '9px 12px', border: '1.5px solid var(--warm)', borderRadius: 8, fontSize: 14, outline: 'none', background: '#fff' }}
                          />
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
            {tabSeniors.length === 0 && (
              <tr><td colSpan={8} style={{ padding: 48, textAlign: 'center', color: 'var(--ink-500)' }}>해당 사업단에 등록된 어르신이 없습니다.</td></tr>
            )}
          </tbody>
        </table>
      </Card>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 4px', marginTop: 8 }}>
        <div style={{ display: 'flex', gap: 12, fontSize: 14, color: 'var(--ink-500)' }}>
          <span>변경: <strong className="num" style={{ color: 'var(--ink-900)', fontWeight: 700 }}>{dirtyCount}</strong>건</span>
          {warnCount > 0 && <span style={{ color: 'var(--warm)' }}>완충구간: <strong className="num">{warnCount}</strong>건</span>}
          {blockedCount > 0 && <span style={{ color: 'var(--danger)' }}>저장불가: <strong className="num">{blockedCount}</strong>건</span>}
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <Button variant="ghost" size="md">취소</Button>
          <Button variant="secondary" size="md">결재 요청</Button>
          <Button variant="primary" size="md" icon={<Icons.check/>}>전체 저장 ({dirtyCount})</Button>
        </div>
      </div>
    </>
  );
}

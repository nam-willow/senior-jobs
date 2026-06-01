import { useState, useEffect, useRef } from 'react';
import type { TabType } from '../types';
import { useAppStore } from '../stores/appStore';
import { useBusinessUnits } from '../hooks/useBusinessUnits';
import { useSeniors } from '../hooks/useSeniors';
import { useWorkRecords } from '../hooks/useWorkRecords';
import { fmt } from '../data/mockData';
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

export function Work({ tab, setTab, focusSenior, setFocusSenior }: WorkProps) {
  const year = useAppStore((s) => s.year);
  const month = useAppStore((s) => s.month);
  const { units, byTab } = useBusinessUnits(year);
  const bu = byTab(tab);
  const { seniors, loading: sLoading } = useSeniors(bu?.id ?? null);
  const { records, loading: rLoading, save, submit, refetch } = useWorkRecords(year, month, bu?.id ?? null);

  const availableTabs = units.map((u) => {
    if (u.type === 'public_benefit') return '공익활동형' as TabType;
    if (u.type === 'social_service') return '사회서비스형' as TabType;
    return '시장형' as TabType;
  });

  const [rows, setRows] = useState<Record<string, RowState>>({});
  const [saving, setSaving] = useState(false);
  const focusRowRef = useRef<HTMLTableRowElement>(null);

  useEffect(() => {
    const next: Record<string, RowState> = {};
    seniors.forEach((s) => {
      const rec = records.find((r) => r.senior_id === s.id);
      next[s.id] = {
        hours: rec ? String(rec.worked_hours) : '',
        amount: rec ? rec.amount_paid : 0,
        dirty: false,
        reason: rec?.overtime_reason ?? '',
      };
    });
    setRows(next);
  }, [seniors, records]);

  useEffect(() => {
    if (focusSenior && focusRowRef.current) {
      focusRowRef.current.scrollIntoView({ block: 'center' });
      const t = setTimeout(() => setFocusSenior(null), 2500);
      return () => clearTimeout(t);
    }
  }, [focusSenior]);

  const handleH = (id: string, raw: string) => {
    const v = raw.replace(/[^\d.]/g, '');
    const n = parseFloat(v) || 0;
    const senior = seniors.find((s) => s.id === id);
    const rate = senior?.hourly_wage ?? 4000;
    setRows((p) => ({ ...p, [id]: { ...p[id], hours: v, amount: v ? Math.round(n * rate) : 0, dirty: true } }));
  };
  const handleReason = (id: string, r: string) => {
    setRows((p) => ({ ...p, [id]: { ...p[id], reason: r } }));
  };

  const dirtyRows = Object.entries(rows).filter(([, r]) => r.dirty);
  const dirtyCount = dirtyRows.length;
  const blockedCount = Object.values(rows).filter((r) => parseFloat(r.hours) > 43).length;
  const warnCount = Object.values(rows).filter((r) => { const h = parseFloat(r.hours)||0; return h > 42 && h <= 43; }).length;

  const handleSaveAll = async () => {
    setSaving(true);
    try {
      const sessionHours = bu?.session_default_hours || 3;
      for (const [id, r] of dirtyRows) {
        const hours = parseFloat(r.hours) || 0;
        if (hours > 43) continue;
        const workedDays = hours > 0 ? Math.ceil(hours / sessionHours) : 0;
        await save(id, { hours, amount: r.amount, workedDays, reason: r.reason || undefined });
      }
      setRows((p) => {
        const next = { ...p };
        dirtyRows.forEach(([id]) => { next[id] = { ...next[id], dirty: false }; });
        return next;
      });
    } finally {
      setSaving(false);
    }
  };

  const handleSubmitAll = async () => {
    const draftRecords = records.filter((r) => r.status === 'DRAFT');
    if (draftRecords.length === 0) { alert('결재 요청할 근무기록이 없습니다 (DRAFT 상태만 가능).'); return; }
    setSaving(true);
    try {
      for (const rec of draftRecords) {
        await submit(rec.id);
      }
      alert(`${draftRecords.length}건이 결재 요청되었습니다.`);
    } catch {
      alert('결재 요청 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
      refetch();
    }
  };

  const loading = sLoading || rLoading;

  return (
    <>
      <UnitTabBar tab={tab} onChange={setTab} availableTabs={availableTabs} right={
        <>
          <span style={{ fontSize: 14, color: 'var(--ink-500)' }}>수정 <strong className="num" style={{ color: dirtyCount > 0 ? 'var(--warm)' : 'var(--ink-700)' }}>{dirtyCount}</strong>건</span>
          <Button variant="secondary" size="sm" icon={<Icons.check/>} onClick={handleSubmitAll}>결재 요청</Button>
          <Button variant="primary" size="sm" icon={<Icons.check/>} onClick={handleSaveAll}>{saving ? '저장 중…' : '전체 저장'}</Button>
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
        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: 'var(--ink-400)' }}>로딩 중…</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
            <thead>
              <tr style={{ background: 'var(--cream-50)' }}>
                {[['어르신 이름','left'],['근무장소','left'],['배정시간','center'],['근무시간 (h)','center'],['지급금액 (원)','right'],['상태','center']].map(([h, a]) => (
                  <th key={h} style={{ padding: '14px 18px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, textAlign: a as 'left'|'center'|'right', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {seniors.map((s) => {
                const r = rows[s.id] || { hours: '', amount: 0, dirty: false, reason: '' };
                const h = parseFloat(r.hours) || 0;
                const overWarn    = h > 42 && h <= 43;
                const overBlocked = h > 43;
                const focused     = focusSenior === s.id.charCodeAt(0);
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
                        <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>{s.birth_date}</div>
                      </td>
                      <td style={{ padding: '14px 18px', color: 'var(--ink-700)' }}>{s.workplace || '—'}</td>
                      <td className="num" style={{ padding: '14px 18px', textAlign: 'center', color: 'var(--ink-500)' }}>{s.allocated_hours}h</td>
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
                        <td colSpan={6} style={{ padding: '12px 18px 16px 36px', borderTop: '1px dashed var(--warm)' }}>
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
              {!loading && seniors.length === 0 && (
                <tr><td colSpan={6} style={{ padding: 48, textAlign: 'center', color: 'var(--ink-500)' }}>해당 사업단에 등록된 어르신이 없습니다.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </Card>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 4px', marginTop: 8 }}>
        <div style={{ display: 'flex', gap: 12, fontSize: 14, color: 'var(--ink-500)' }}>
          <span>변경: <strong className="num" style={{ color: 'var(--ink-900)', fontWeight: 700 }}>{dirtyCount}</strong>건</span>
          {warnCount > 0 && <span style={{ color: 'var(--warm)' }}>완충구간: <strong className="num">{warnCount}</strong>건</span>}
          {blockedCount > 0 && <span style={{ color: 'var(--danger)' }}>저장불가: <strong className="num">{blockedCount}</strong>건</span>}
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <Button variant="ghost" size="md">취소</Button>
          <Button variant="secondary" size="md" onClick={handleSubmitAll}>결재 요청</Button>
          <Button variant="primary" size="md" icon={<Icons.check/>} onClick={handleSaveAll}>
            {saving ? '저장 중…' : `전체 저장 (${dirtyCount})`}
          </Button>
        </div>
      </div>
    </>
  );
}

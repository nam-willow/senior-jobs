import type { TabType } from '../types';
import { useAppStore } from '../stores/appStore';
import { useBusinessUnits } from '../hooks/useBusinessUnits';
import { useSeniors } from '../hooks/useSeniors';
import { useWorkRecords } from '../hooks/useWorkRecords';
import { useBudget } from '../hooks/useBudget';
import { fmt, won } from '../data/mockData';
import { UnitTabBar } from '../components/layout/UnitTabBar';
import { BudgetStrip } from '../components/layout/BudgetStrip';
import { AlertBox } from '../components/layout/AlertBox';
import { Card } from '../components/layout/Card';
import { Progress } from '../components/shared/Progress';
import { Button } from '../components/shared/Button';
import { Icons } from '../components/shared/Icons';

interface SalaryProps {
  tab: TabType;
  setTab: (t: TabType) => void;
  year: number;
  month: number;
}

function downloadSalary(year: number, month: number, buId: string | null, format: 'excel' | 'pdf') {
  const params = new URLSearchParams({ format });
  if (buId) params.append('business_unit_id', buId);
  const token = localStorage.getItem('access_token') ?? '';
  const ext = format === 'excel' ? 'xlsx' : 'pdf';
  fetch(`/api/v1/work-logs/salary-statement/${year}/${month}?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((r) => {
      if (!r.ok) throw new Error('no approved records');
      return r.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `salary_${year}_${String(month).padStart(2, '0')}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    })
    .catch(() => alert('다운로드 실패. 승인된 근무기록이 없을 수 있습니다.'));
}

export function Salary({ tab, setTab, year, month }: SalaryProps) {
  const storeYear = useAppStore((s) => s.year);
  const { units, byTab } = useBusinessUnits(storeYear);
  const bu = byTab(tab);
  const { seniors, loading: sLoading } = useSeniors(bu?.id ?? null);
  const { records, loading: rLoading } = useWorkRecords(year, month, bu?.id ?? null);
  const { totalBudget, totalSpent, remaining, pct, loading: bLoading } = useBudget(bu?.id ?? null, year);

  const availableTabs = units.map((u) => {
    if (u.type === 'public_benefit') return '공익활동형' as TabType;
    if (u.type === 'social_service') return '사회서비스형' as TabType;
    return '시장형' as TabType;
  });

  const approvedRecords = records.filter((r) => r.status === 'APPROVED');

  const rows = seniors.map((s) => {
    const rec = approvedRecords.find((r) => r.senior_id === s.id);
    return {
      ...s,
      hours: rec?.worked_hours ?? 0,
      amount: rec?.amount_paid ?? 0,
    };
  });

  const totalH = rows.reduce((sum, r) => sum + r.hours, 0);
  const totalA = rows.reduce((sum, r) => sum + r.amount, 0);
  const loading = sLoading || rLoading || bLoading;

  return (
    <>
      <UnitTabBar tab={tab} onChange={setTab} availableTabs={availableTabs} right={
        <>
          <Button variant="secondary" size="sm" icon={<Icons.download/>}
            onClick={() => downloadSalary(year, month, bu?.id ?? null, 'excel')}>Excel</Button>
          <Button variant="secondary" size="sm" icon={<Icons.download/>}
            onClick={() => downloadSalary(year, month, bu?.id ?? null, 'pdf')}>PDF</Button>
          <Button variant="primary" size="sm" icon={<Icons.doc/>}
            onClick={() => window.print()}>인쇄</Button>
        </>
      }/>

      <BudgetStrip tab={tab}/>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 18 }}>
        <Card padding="16px 20px">
          <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>연간 총 사업비</div>
          <div className="num" style={{ fontSize: 24, fontWeight: 800, color: 'var(--ink-900)', marginTop: 4 }}>{won(totalBudget)}</div>
          <div style={{ fontSize: 12, color: 'var(--ink-400)', marginTop: 2 }}>임금 + 담당자 + 사업진행비</div>
        </Card>
        <Card padding="16px 20px" style={{ borderLeft: '4px solid var(--green-600)' }}>
          <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>현재까지 사용</div>
          <div className="num" style={{ fontSize: 24, fontWeight: 800, color: 'var(--green-600)', marginTop: 4 }}>{won(totalSpent)}</div>
          <Progress value={pct} color="var(--green-600)" height={6}/>
          <div className="num" style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 4 }}>{pct}% 집행</div>
        </Card>
        <Card padding="16px 20px" style={{ borderLeft: '4px solid var(--green-600)' }}>
          <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>잔여 사업비</div>
          <div className="num" style={{ fontSize: 24, fontWeight: 800, color: remaining >= 0 ? 'var(--green-700)' : 'var(--danger)', marginTop: 4 }}>{won(remaining)}</div>
          <div style={{ fontSize: 12, color: 'var(--ink-400)', marginTop: 2 }}>{100 - pct}% 남음</div>
        </Card>
      </div>

      <AlertBox tone="warn">
        <strong>승인(APPROVED)</strong> 상태만 포함됩니다. DRAFT · SUBMITTED 상태 근무기록은 제외됩니다.
      </AlertBox>

      <div style={{ background: 'var(--green-700)', color: '#fff', padding: '14px 22px', borderRadius: '16px 16px 0 0', textAlign: 'center', fontSize: 16, fontWeight: 700 }}>
        {year}년 {month}월 노인일자리 급여대장 — {tab} 사업단
      </div>

      <Card padding="0" style={{ borderRadius: '0 0 18px 18px' }}>
        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: 'var(--ink-400)' }}>로딩 중…</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
            <thead>
              <tr style={{ background: 'var(--cream-50)' }}>
                {['번호', '이름', '생년월일', '근무시간', '지급금액', '서명'].map((h, i) => (
                  <th key={h} style={{ padding: '14px 16px', textAlign: i === 4 ? 'right' : 'center', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, borderBottom: '1.5px solid var(--line)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.id} style={{ borderTop: '1px solid var(--line-soft)' }}>
                  <td style={{ padding: '14px 16px', textAlign: 'center', color: 'var(--ink-500)' }}>{i + 1}</td>
                  <td style={{ padding: '14px 16px', textAlign: 'center', fontWeight: 700, color: 'var(--ink-900)' }}>{r.name}</td>
                  <td className="num" style={{ padding: '14px 16px', textAlign: 'center', color: 'var(--ink-700)' }}>{r.birth_date ? r.birth_date.replace(/-/g, '.') : '—'}</td>
                  <td className="num" style={{ padding: '14px 16px', textAlign: 'center', color: 'var(--ink-700)' }}>{r.hours}h</td>
                  <td className="num" style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 700, color: r.amount ? 'var(--ink-900)' : 'var(--ink-400)' }}>
                    {r.amount ? fmt(r.amount) + '원' : '—'}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                    <div style={{ width: 60, height: 28, margin: '0 auto', border: '1px dashed var(--line)', borderRadius: 4, fontSize: 11, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-400)' }}>(인)</div>
                  </td>
                </tr>
              ))}
              {!loading && rows.length === 0 && (
                <tr><td colSpan={6} style={{ padding: 48, textAlign: 'center', color: 'var(--ink-400)' }}>이 사업단에 등록된 어르신이 없습니다.</td></tr>
              )}
            </tbody>
            {rows.length > 0 && (
              <tfoot>
                <tr style={{ background: 'var(--cream-50)', borderTop: '2px solid var(--line)' }}>
                  <td colSpan={3} style={{ padding: '14px 16px', textAlign: 'center', fontWeight: 800, color: 'var(--ink-900)' }}>합계</td>
                  <td className="num" style={{ padding: '14px 16px', textAlign: 'center', fontWeight: 800 }}>{totalH}h</td>
                  <td className="num" style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 800, color: 'var(--green-700)' }}>{fmt(totalA)}원</td>
                  <td/>
                </tr>
              </tfoot>
            )}
          </table>
        )}
      </Card>
    </>
  );
}

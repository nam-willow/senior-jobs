import type { TabType } from '../types';
import { SENIORS, BUDGET, fmt, won } from '../data/mockData';
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

const HOURS_BY_NAME: Record<string, number> = {
  '김영자': 30, '박철수': 28, '이순희': 30, '최대호': 42, '정미숙': 30,
  '한상호': 30, '윤정숙': 24, '강민준': 36, '박영순': 0,  '장순자': 30,
  '오영자': 28, '신복례': 30,
};
const RATE = 4000;

export function Salary({ tab, setTab, year, month }: SalaryProps) {
  const tabSeniors = SENIORS.filter((s) => s.unit === tab);
  const rows = tabSeniors.map((s) => ({ ...s, hours: HOURS_BY_NAME[s.name] || 0, amount: (HOURS_BY_NAME[s.name] || 0) * RATE }));
  const totalH = rows.reduce((s, r) => s + r.hours, 0);
  const totalA = rows.reduce((s, r) => s + r.amount, 0);
  const b = BUDGET[tab];

  return (
    <>
      <UnitTabBar tab={tab} onChange={setTab} right={
        <>
          <Button variant="secondary" size="sm" icon={<Icons.download/>}>Excel</Button>
          <Button variant="secondary" size="sm" icon={<Icons.download/>}>PDF</Button>
          <Button variant="primary" size="sm" icon={<Icons.doc/>}>인쇄</Button>
        </>
      }/>

      <BudgetStrip tab={tab}/>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 18 }}>
        <Card padding="16px 20px">
          <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>연간 총 사업비</div>
          <div className="num" style={{ fontSize: 24, fontWeight: 800, color: 'var(--ink-900)', marginTop: 4 }}>{won(b.total)}</div>
          <div style={{ fontSize: 12, color: 'var(--ink-400)', marginTop: 2 }}>임금 + 담당자 + 사업진행비</div>
        </Card>
        <Card padding="16px 20px" style={{ borderLeft: `4px solid ${b.color}` }}>
          <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>현재까지 사용</div>
          <div className="num" style={{ fontSize: 24, fontWeight: 800, color: b.color, marginTop: 4 }}>{won(b.used)}</div>
          <Progress value={b.pct} color={b.color} height={6}/>
          <div className="num" style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 4 }}>{b.pct}% · 1~5월</div>
        </Card>
        <Card padding="16px 20px" style={{ borderLeft: '4px solid var(--green-600)' }}>
          <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>잔여 사업비</div>
          <div className="num" style={{ fontSize: 24, fontWeight: 800, color: 'var(--green-700)', marginTop: 4 }}>{won(b.remain)}</div>
          <div style={{ fontSize: 12, color: 'var(--ink-400)', marginTop: 2 }}>6~11월 (6개월)</div>
        </Card>
      </div>

      <AlertBox tone="warn">
        <strong>승인(APPROVED)</strong> 상태만 포함됩니다. DRAFT · SUBMITTED 상태 근무기록은 제외됩니다.
      </AlertBox>

      <div style={{ background: 'var(--green-700)', color: '#fff', padding: '14px 22px', borderRadius: '16px 16px 0 0', textAlign: 'center', fontSize: 16, fontWeight: 700 }}>
        {year}년 {month}월 노인일자리 급여대장 — {tab} 사업단
      </div>

      <Card padding="0" style={{ borderRadius: '0 0 18px 18px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
          <thead>
            <tr style={{ background: 'var(--cream-50)' }}>
              {['번호', '이름', '생년월일', '근무시간', '지급금액', '서명', '등록 사복사'].map((h, i) => (
                <th key={h} style={{ padding: '14px 16px', textAlign: i === 4 ? 'right' : 'center', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, borderBottom: '1.5px solid var(--line)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.id} style={{ borderTop: '1px solid var(--line-soft)' }}>
                <td style={{ padding: '14px 16px', textAlign: 'center', color: 'var(--ink-500)' }}>{i + 1}</td>
                <td style={{ padding: '14px 16px', textAlign: 'center', fontWeight: 700, color: 'var(--ink-900)' }}>{r.name}</td>
                <td className="num" style={{ padding: '14px 16px', textAlign: 'center', color: 'var(--ink-700)' }}>{r.birth.replace(/\./g, '').slice(2, 8)}</td>
                <td className="num" style={{ padding: '14px 16px', textAlign: 'center', color: 'var(--ink-700)' }}>{r.hours}h</td>
                <td className="num" style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 700, color: r.amount ? 'var(--ink-900)' : 'var(--ink-400)' }}>
                  {r.amount ? fmt(r.amount) + '원' : '—'}
                </td>
                <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                  <div style={{ width: 60, height: 28, margin: '0 auto', border: '1px dashed var(--line)', borderRadius: 4, fontSize: 11, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-400)' }}>(인)</div>
                </td>
                <td style={{ padding: '14px 16px', textAlign: 'center', color: 'var(--green-700)', fontWeight: 600 }}>{r.sw}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr style={{ background: 'var(--cream-50)', borderTop: '2px solid var(--line)' }}>
              <td colSpan={3} style={{ padding: '14px 16px', textAlign: 'center', fontWeight: 800, color: 'var(--ink-900)' }}>합계</td>
              <td className="num" style={{ padding: '14px 16px', textAlign: 'center', fontWeight: 800 }}>{totalH}h</td>
              <td className="num" style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 800, color: 'var(--green-700)' }}>{fmt(totalA)}원</td>
              <td colSpan={2}/>
            </tr>
          </tfoot>
        </table>
      </Card>

      <div style={{ marginTop: 16, fontSize: 12, color: 'var(--ink-400)', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
        출력 시 document_snapshots에 자동 저장
      </div>
    </>
  );
}

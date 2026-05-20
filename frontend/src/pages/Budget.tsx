import { useState } from 'react';
import type { TabType } from '../types';
import { BUDGET, fmt, won } from '../data/mockData';
import { UnitTabBar } from '../components/layout/UnitTabBar';
import { BudgetStrip } from '../components/layout/BudgetStrip';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Button } from '../components/shared/Button';
import { Icons } from '../components/shared/Icons';

const EXPENSES: Record<TabType, { d: string; cat: string; item: string; amt: number; note: string; tone: string }[]> = {
  '공익활동형': [
    { d: '2026.05.10', cat: '어르신 임금', item: '5월 활동비',    amt: 1200000, note: '120명',     tone: 'green'  },
    { d: '2026.05.02', cat: '사업진행비',  item: '회의 다과비',  amt: 45000,   note: '월례 회의', tone: 'warm'   },
    { d: '2026.04.30', cat: '담당자 임금', item: '4월 인건비',    amt: 2000000, note: '사복사 2인', tone: 'danger' },
    { d: '2026.04.10', cat: '어르신 임금', item: '4월 활동비',    amt: 1200000, note: '120명',     tone: 'green'  },
    { d: '2026.04.05', cat: '사업진행비',  item: '안전조끼 구매', amt: 320000,  note: '30벌',      tone: 'warm'   },
    { d: '2026.03.15', cat: '어르신 임금', item: '3월 활동비',    amt: 1180000, note: '118명',     tone: 'green'  },
  ],
  '사회서비스형': [
    { d: '2026.05.12', cat: '어르신 임금', item: '5월 활동비', amt: 3060000, note: '85명',     tone: 'green'  },
    { d: '2026.05.01', cat: '담당자 임금', item: '5월 인건비', amt: 1200000, note: '사복사 3인', tone: 'danger' },
    { d: '2026.04.20', cat: '어르신 임금', item: '4월 활동비', amt: 2890000, note: '82명',     tone: 'green'  },
  ],
  '시장형': [
    { d: '2026.05.08', cat: '어르신 임금', item: '5월 활동비', amt: 540000, note: '42명', tone: 'green'  },
    { d: '2026.04.22', cat: '담당자 임금', item: '4월 인건비', amt: 500000, note: '1인',  tone: 'danger' },
    { d: '2026.04.10', cat: '어르신 임금', item: '4월 활동비', amt: 525000, note: '42명', tone: 'green'  },
  ],
};

const INCOMES = [
  { d: '2026.01.10', src: '보건복지부', item: '2026년도 1차 보조금', amt: 9000000 },
  { d: '2026.04.10', src: '보건복지부', item: '2026년도 2차 보조금', amt: 5400000 },
];

interface BudgetProps {
  tab: TabType;
  setTab: (t: TabType) => void;
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 12px', border: '1.5px solid var(--line)',
  borderRadius: 10, fontSize: 14, outline: 'none', background: '#fff', color: 'var(--ink-900)',
  display: 'block',
};

export function Budget({ tab, setTab }: BudgetProps) {
  const b = BUDGET[tab];
  const items = EXPENSES[tab] || [];
  const totalExp = items.reduce((s, x) => s + x.amt, 0);
  const totalInc = INCOMES.reduce((s, x) => s + x.amt, 0);
  const balance  = totalInc - totalExp;
  const [section, setSection] = useState<'expense'|'income'>('expense');

  return (
    <>
      <UnitTabBar tab={tab} onChange={setTab} right={
        <Button variant="secondary" size="sm" icon={<Icons.download/>}>전체 내보내기</Button>
      }/>

      <BudgetStrip tab={tab}/>

      <div className="g4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 22 }}>
        {[
          { lb: '총 사업비 (예산)',  val: won(b.total),  sub: '보건복지부 보조금',      color: 'var(--ink-900)' },
          { lb: '수입 누계',         val: won(totalInc), sub: `${INCOMES.length}건 입금`, color: 'var(--info)'    },
          { lb: '지출 누계',         val: won(b.used),   sub: `${items.length}건 등록`,  color: b.color          },
          { lb: '잔액',              val: won(b.remain), sub: `${100 - b.pct}% 남음`,    color: 'var(--green-700)' },
        ].map((s) => (
          <div key={s.lb} style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 18, padding: '18px 22px', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>{s.lb}</div>
            <div className="num" style={{ fontSize: 22, fontWeight: 800, color: s.color, marginTop: 6, lineHeight: 1.1 }}>{s.val}</div>
            <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 6 }}>{s.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 20 }}>
        {/* form */}
        <Card padding="0">
          <div style={{ display: 'flex', borderBottom: '1px solid var(--line)' }}>
            {([['expense', '지출 등록'], ['income', '수입 등록']] as [string,string][]).map(([k, l]) => (
              <div key={k} onClick={() => setSection(k as 'expense'|'income')} style={{
                flex: 1, padding: '14px 0', textAlign: 'center', cursor: 'pointer',
                fontSize: 14, fontWeight: section === k ? 700 : 500,
                color: section === k ? 'var(--green-800)' : 'var(--ink-500)',
                background: section === k ? 'var(--green-50)' : '#fff',
                borderBottom: section === k ? '2px solid var(--green-700)' : 'none',
              }}>{l}</div>
            ))}
          </div>
          <div style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 14 }}>
            {[
              { label: section === 'expense' ? '지출일자' : '수입일자', el: <input type="date" defaultValue="2026-05-19" style={inputStyle}/> },
              { label: '항목명', el: <input type="text" placeholder={section === 'expense' ? '예: 5월 활동비' : '예: 2026년도 3차 보조금'} style={inputStyle}/> },
              {
                label: section === 'expense' ? '항목 구분' : '수입처',
                el: section === 'expense'
                  ? <select style={inputStyle}><option>어르신 임금</option><option>담당자 임금</option><option>사업진행비</option></select>
                  : <input type="text" placeholder="예: 보건복지부" style={inputStyle}/>,
              },
              { label: '금액 (원)', el: <input type="number" placeholder="0" style={inputStyle}/> },
              { label: '비고', el: <textarea rows={3} placeholder="메모" style={{ ...inputStyle, resize: 'vertical' }}/> },
            ].map((r) => (
              <div key={r.label}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-700)', marginBottom: 6 }}>{r.label}</div>
                {r.el}
              </div>
            ))}
            <Button variant="primary" size="md" full icon={<Icons.plus/>}>{section === 'expense' ? '지출 등록' : '수입 등록'}</Button>
          </div>
        </Card>

        {/* list */}
        <div>
          <Card title={section === 'expense' ? `지출 내역 — ${tab}` : '수입 내역'} right={<Button variant="ghost" size="sm" icon={<Icons.download/>}>Excel</Button>} padding="0">
            {section === 'expense' ? (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
                <thead>
                  <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
                    {['지출일자', '구분', '항목', '금액', '비고', ''].map((h, i) => (
                      <th key={h} style={{ padding: '12px 18px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, textAlign: i === 3 ? 'right' : 'left' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {items.map((e, i) => (
                    <tr key={i} style={{ borderTop: '1px solid var(--line-soft)' }}>
                      <td className="num" style={{ padding: '13px 18px', color: 'var(--ink-700)' }}>{e.d}</td>
                      <td style={{ padding: '13px 18px' }}>
                        <Chip tone={e.tone === 'green' ? 'green' : e.tone === 'warm' ? 'warm' : 'danger'} size="sm">{e.cat}</Chip>
                      </td>
                      <td style={{ padding: '13px 18px', fontWeight: 600, color: 'var(--ink-900)' }}>{e.item}</td>
                      <td className="num" style={{ padding: '13px 18px', textAlign: 'right', fontWeight: 700, color: 'var(--ink-900)' }}>{fmt(e.amt)}원</td>
                      <td style={{ padding: '13px 18px', fontSize: 13, color: 'var(--ink-500)' }}>{e.note}</td>
                      <td style={{ padding: '13px 18px' }}><Button variant="ghost" size="sm">수정</Button></td>
                    </tr>
                  ))}
                  <tr style={{ background: 'var(--cream-50)', borderTop: '2px solid var(--line)' }}>
                    <td colSpan={3} style={{ padding: '14px 18px', fontWeight: 800 }}>합계 ({items.length}건)</td>
                    <td className="num" style={{ padding: '14px 18px', textAlign: 'right', fontWeight: 800, color: b.color }}>{fmt(totalExp)}원</td>
                    <td colSpan={2}/>
                  </tr>
                </tbody>
              </table>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
                <thead>
                  <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
                    {['수입일자', '수입처', '항목', '금액'].map((h, i) => (
                      <th key={h} style={{ padding: '12px 18px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, textAlign: i === 3 ? 'right' : 'left' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {INCOMES.map((e, i) => (
                    <tr key={i} style={{ borderTop: '1px solid var(--line-soft)' }}>
                      <td className="num" style={{ padding: '13px 18px', color: 'var(--ink-700)' }}>{e.d}</td>
                      <td style={{ padding: '13px 18px', fontWeight: 600, color: 'var(--info)' }}>{e.src}</td>
                      <td style={{ padding: '13px 18px', color: 'var(--ink-900)' }}>{e.item}</td>
                      <td className="num" style={{ padding: '13px 18px', textAlign: 'right', fontWeight: 700, color: 'var(--info)' }}>+ {fmt(e.amt)}원</td>
                    </tr>
                  ))}
                  <tr style={{ background: 'var(--cream-50)', borderTop: '2px solid var(--line)' }}>
                    <td colSpan={3} style={{ padding: '14px 18px', fontWeight: 800 }}>합계 ({INCOMES.length}건)</td>
                    <td className="num" style={{ padding: '14px 18px', textAlign: 'right', fontWeight: 800, color: 'var(--info)' }}>{fmt(totalInc)}원</td>
                  </tr>
                </tbody>
              </table>
            )}
          </Card>

          <div style={{ marginTop: 14, padding: '14px 18px', background: balance >= 0 ? 'var(--green-50)' : '#FBE3E3', border: `1px solid ${balance >= 0 ? 'var(--green-200)' : '#EBBCBC'}`, borderRadius: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 15, fontWeight: 700, color: balance >= 0 ? 'var(--green-800)' : 'var(--danger)' }}>
              {balance >= 0 ? '✓ 수입·지출 균형 정상' : '⚠️ 지출 초과'}
            </span>
            <span className="num" style={{ fontSize: 16, fontWeight: 800, color: balance >= 0 ? 'var(--green-700)' : 'var(--danger)' }}>
              잔액 {fmt(balance)}원
            </span>
          </div>
        </div>
      </div>
    </>
  );
}

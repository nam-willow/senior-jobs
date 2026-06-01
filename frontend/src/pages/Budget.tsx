import { useState } from 'react';
import type { TabType } from '../types';
import { useAppStore } from '../stores/appStore';
import { useBusinessUnits } from '../hooks/useBusinessUnits';
import { useBudget } from '../hooks/useBudget';
import { api } from '../lib/api';
import { TAB_TONE, fmt, won } from '../data/mockData';
import { UnitTabBar } from '../components/layout/UnitTabBar';
import { BudgetStrip } from '../components/layout/BudgetStrip';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Button } from '../components/shared/Button';
import { Icons } from '../components/shared/Icons';

const CAT_LABEL: Record<string, string> = {
  wage: '어르신 임금', manager_wage: '담당자 임금', operation: '사업진행비',
};
const CAT_TONE: Record<string, 'green' | 'warm' | 'danger'> = {
  wage: 'green', manager_wage: 'danger', operation: 'warm',
};

interface BudgetProps {
  tab: TabType;
  setTab: (t: TabType) => void;
}

export function Budget({ tab, setTab }: BudgetProps) {
  const year = useAppStore((s) => s.year);
  const { units, byTab } = useBusinessUnits(year);
  const bu = byTab(tab);
  const { budget, expenseRows, loading, totalBudget, totalSpent, remaining, pct, refetch } = useBudget(bu?.type ?? null, year);
  const color = TAB_TONE[tab].color;
  const [section, setSection] = useState<'expense' | 'income'>('expense');

  const [formDate, setFormDate] = useState('');
  const [formItem, setFormItem] = useState('');
  // 어르신 임금(wage)은 근무등록에서 자동 집계되므로 수동 등록 대상에서 제외
  const [formCategory, setFormCategory] = useState<'manager_wage' | 'operation'>('manager_wage');
  const [formAmount, setFormAmount] = useState('');
  const [formNote, setFormNote] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // 예산 등록 모달
  const [showBudgetModal, setShowBudgetModal] = useState(false);
  const [budgetWage, setBudgetWage] = useState('');
  const [budgetMgr, setBudgetMgr] = useState('');
  const [budgetOp, setBudgetOp] = useState('');
  const [budgetSeniorCount, setBudgetSeniorCount] = useState('');
  const [budgetHourlyWage, setBudgetHourlyWage] = useState('');
  const [budgetSubmitting, setBudgetSubmitting] = useState(false);

  // ── 예산 등록 폼 파생값 ──────────────────────────────────────────────
  const wageNum = parseInt(budgetWage || '0', 10);
  const mgrNum = parseInt(budgetMgr || '0', 10);
  const opNum = parseInt(budgetOp || '0', 10);
  const seniorCountNum = parseInt(budgetSeniorCount || '0', 10);
  const hourlyNum = parseInt(budgetHourlyWage || '0', 10);
  // 총사업비 = 세 항목 합 (자동 계산)
  const totalBudgetForm = wageNum + mgrNum + opNum;
  // 검증 기준: 시급 × 연간 배정시간 × 인원 == 어르신 임금 예산
  const annualHours = bu?.total_annual_hours ?? 0;
  const expectedWage = hourlyNum * annualHours * seniorCountNum;
  // 시급·인원·연간시간이 모두 입력됐을 때만 검증. 불일치 시 경고 → 저장 차단
  const canValidateWage = hourlyNum > 0 && seniorCountNum > 0 && annualHours > 0;
  const wageMismatch = canValidateWage && expectedWage !== wageNum;

  const handleCreateBudget = async () => {
    if (!bu || wageMismatch) return;
    setBudgetSubmitting(true);
    try {
      await api.post('/budgets/', {
        business_unit_id: bu.id,
        year,
        total_wage_budget: wageNum,
        manager_wage_budget: mgrNum,
        operation_budget: opNum,
        senior_count: seniorCountNum,
        hourly_wage: hourlyNum,
      });
      setBudgetWage(''); setBudgetMgr(''); setBudgetOp(''); setBudgetSeniorCount(''); setBudgetHourlyWage('');
      setShowBudgetModal(false);
      refetch();
    } catch {
      alert('예산 등록 중 오류가 발생했습니다.');
    } finally {
      setBudgetSubmitting(false);
    }
  };

  const availableTabs = units.map((u) => {
    if (u.type === 'public_benefit') return '공익활동형' as TabType;
    if (u.type === 'social_service') return '사회서비스형' as TabType;
    return '시장형' as TabType;
  });

  const handleSubmitExpense = async () => {
    if (!budget || !formDate || !formItem || !formAmount) return;
    setSubmitting(true);
    try {
      await api.post('/budgets/expenditures/', {
        annual_budget_id: budget.id,
        category: formCategory,
        item_name: formItem,
        amount: parseInt(formAmount, 10),
        expense_date: formDate,
        note: formNote || null,
      });
      setFormDate('');
      setFormItem('');
      setFormAmount('');
      setFormNote('');
      refetch();
    } catch {
      alert('지출 등록 중 오류가 발생했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExcelDownload = () => {
    if (!bu) return;
    const token = localStorage.getItem('access_token');
    const url = `/api/v1/work-logs/salary-statement/${year}/all?format=excel&business_unit_id=${bu.id}`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `expenditures_${tab}_${year}.xlsx`;
        link.click();
      })
      .catch(() => alert('다운로드에 실패했습니다.'));
  };

  return (
    <>
      <UnitTabBar tab={tab} onChange={setTab} availableTabs={availableTabs} right={
        <Button variant="secondary" size="sm" icon={<Icons.download/>} onClick={handleExcelDownload}>전체 내보내기</Button>
      }/>

      <BudgetStrip tab={tab}/>

      <div className="g4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 22 }}>
        {[
          { lb: '총 사업비 (예산)', val: won(totalBudget), sub: '연간 예산', color: 'var(--ink-900)' },
          { lb: '지출 누계',        val: won(totalSpent),  sub: `${expenseRows.length}건 등록`, color },
          { lb: '잔액',             val: won(remaining),   sub: `${100 - pct}% 남음`, color: remaining < 0 ? 'var(--danger)' : 'var(--green-700)' },
          { lb: '집행률',           val: `${pct}%`,        sub: '대비 지출', color: pct > 90 ? 'var(--danger)' : 'var(--ink-900)' },
        ].map((s) => (
          <div key={s.lb} style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 18, padding: '18px 22px', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>{s.lb}</div>
            <div className="num" style={{ fontSize: 22, fontWeight: 800, color: s.color, marginTop: 6, lineHeight: 1.1 }}>{s.val}</div>
            <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 6 }}>{s.sub}</div>
          </div>
        ))}
      </div>

      {/* 사업단 없음 */}
      {!loading && !bu && (
        <Card padding="40px">
          <div style={{ textAlign: 'center', color: 'var(--ink-500)' }}>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{tab} 사업단이 등록되지 않았습니다.</div>
            <div style={{ fontSize: 13 }}>사업단 관리 메뉴에서 먼저 사업단을 등록해 주세요.</div>
          </div>
        </Card>
      )}

      {/* 예산 미등록 */}
      {!loading && bu && !budget && (
        <Card padding="40px">
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink-900)', marginBottom: 8 }}>
              {year}년도 {tab} 예산이 등록되지 않았습니다.
            </div>
            <div style={{ fontSize: 13, color: 'var(--ink-500)', marginBottom: 22 }}>
              연간 예산을 등록하면 지출 관리와 집행률 현황을 확인할 수 있습니다.
            </div>
            <Button variant="primary" size="md" icon={<Icons.plus/>} onClick={() => setShowBudgetModal(true)}>
              연간 예산 등록
            </Button>
          </div>
        </Card>
      )}

      {bu && budget && (
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 20 }}>
          <Card padding="0">
            <div style={{ display: 'flex', borderBottom: '1px solid var(--line)' }}>
              {([['expense', '지출 등록'], ['income', '수입 등록']] as [string, string][]).map(([k, l]) => (
                <div key={k} onClick={() => setSection(k as 'expense' | 'income')} style={{
                  flex: 1, padding: '14px 0', textAlign: 'center', cursor: 'pointer',
                  fontSize: 14, fontWeight: section === k ? 700 : 500,
                  color: section === k ? 'var(--green-700)' : 'var(--ink-500)',
                  background: section === k ? 'var(--green-50)' : '#fff',
                  borderBottom: section === k ? '2px solid var(--green-700)' : 'none',
                }}>{l}</div>
              ))}
            </div>
            <div style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 14 }}>
              {section === 'expense' ? (
                <>
                  <div>
                    <div style={labelStyle}>지출일자</div>
                    <input type="date" value={formDate} onChange={(e) => setFormDate(e.target.value)} style={inputStyle}/>
                  </div>
                  <div>
                    <div style={labelStyle}>항목명</div>
                    <input type="text" value={formItem} onChange={(e) => setFormItem(e.target.value)} placeholder="예: 5월 활동비" style={inputStyle}/>
                  </div>
                  <div>
                    <div style={labelStyle}>항목 구분</div>
                    <select value={formCategory} onChange={(e) => setFormCategory(e.target.value as typeof formCategory)} style={inputStyle}>
                      <option value="manager_wage">담당자 임금</option>
                      <option value="operation">사업진행비</option>
                    </select>
                    <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 6, lineHeight: 1.4 }}>
                      ※ 어르신 임금은 [월별 근무 등록]에서 <strong>승인된 근무기록</strong>으로 자동 집계됩니다.
                    </div>
                  </div>
                  <div>
                    <div style={labelStyle}>금액 (원)</div>
                    <input type="number" value={formAmount} onChange={(e) => setFormAmount(e.target.value)} placeholder="0" style={inputStyle}/>
                  </div>
                  <div>
                    <div style={labelStyle}>비고</div>
                    <textarea rows={3} value={formNote} onChange={(e) => setFormNote(e.target.value)} placeholder="메모" style={{ ...inputStyle, resize: 'vertical' }}/>
                  </div>
                  <Button
                    variant="primary" size="md" full icon={<Icons.plus/>}
                    onClick={handleSubmitExpense}
                    disabled={submitting || !formDate || !formItem || !formAmount}
                  >
                    {submitting ? '등록 중…' : '지출 등록'}
                  </Button>
                </>
              ) : (
                <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--ink-400)', fontSize: 14 }}>수입 내역은 예산 등록 시 자동 집계됩니다.</div>
              )}
            </div>
          </Card>

          <div>
            <Card title={section === 'expense' ? `지출 내역 — ${tab}` : '수입 내역'} right={
              <Button variant="ghost" size="sm" icon={<Icons.download/>} onClick={handleExcelDownload}>Excel</Button>
            } padding="0">
              {loading ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)' }}>로딩 중…</div>
              ) : section === 'expense' ? (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
                  <thead>
                    <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
                      {['지출일자', '구분', '항목', '금액', '비고', ''].map((h, i) => (
                        <th key={h} style={{ padding: '12px 18px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, textAlign: i === 3 ? 'right' : 'left' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {expenseRows.length === 0 ? (
                      <tr><td colSpan={6} style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)' }}>
                        등록된 지출이 없습니다.
                      </td></tr>
                    ) : expenseRows.map((e) => (
                      <tr key={e.id} style={{ borderTop: '1px solid var(--line-soft)' }}>
                        <td className="num" style={{ padding: '13px 18px', color: 'var(--ink-700)' }}>{e.display_date}</td>
                        <td style={{ padding: '13px 18px' }}>
                          <Chip tone={(CAT_TONE[e.category] ?? 'neutral') as 'green' | 'warm' | 'danger'} size="sm">{CAT_LABEL[e.category] ?? e.category}</Chip>
                        </td>
                        <td style={{ padding: '13px 18px', fontWeight: 600, color: 'var(--ink-900)' }}>{e.item_name}</td>
                        <td className="num" style={{ padding: '13px 18px', textAlign: 'right', fontWeight: 700 }}>{fmt(e.amount)}원</td>
                        <td style={{ padding: '13px 18px', fontSize: 13, color: 'var(--ink-500)' }}>{e.note ?? '—'}</td>
                        <td style={{ padding: '13px 18px' }}>
                          {e.deletable ? (
                            <Button variant="ghost" size="sm" onClick={async () => {
                              if (!confirm('이 지출을 삭제하시겠습니까?')) return;
                              await api.delete(`/budgets/expenditures/${e.id}`);
                              refetch();
                            }}>삭제</Button>
                          ) : (
                            <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>근무등록</span>
                          )}
                        </td>
                      </tr>
                    ))}
                    {expenseRows.length > 0 && (
                      <tr style={{ background: 'var(--cream-50)', borderTop: '2px solid var(--line)' }}>
                        <td colSpan={3} style={{ padding: '14px 18px', fontWeight: 800 }}>합계 ({expenseRows.length}건)</td>
                        <td className="num" style={{ padding: '14px 18px', textAlign: 'right', fontWeight: 800, color }}>{fmt(totalSpent)}원</td>
                        <td colSpan={2}/>
                      </tr>
                    )}
                  </tbody>
                </table>
              ) : (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)' }}>수입 내역은 예산 등록 시 자동 집계됩니다.</div>
              )}
            </Card>

            <div style={{ marginTop: 14, padding: '14px 18px', background: remaining >= 0 ? 'var(--green-50)' : '#FBE3E3', border: `1px solid ${remaining >= 0 ? 'var(--green-200)' : '#EBBCBC'}`, borderRadius: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 15, fontWeight: 700, color: remaining >= 0 ? 'var(--green-700)' : 'var(--danger)' }}>
                {remaining >= 0 ? '✓ 예산 잔액 정상' : '⚠️ 예산 초과'}
              </span>
              <span className="num" style={{ fontSize: 16, fontWeight: 800, color: remaining >= 0 ? 'var(--green-700)' : 'var(--danger)' }}>
                잔액 {fmt(remaining)}원
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 예산 등록 모달 */}
      {showBudgetModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={(e) => { if (e.target === e.currentTarget) setShowBudgetModal(false); }}>
          <div style={{ background: '#fff', borderRadius: 20, padding: '32px 36px', width: 480, boxShadow: '0 8px 40px rgba(0,0,0,0.18)' }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--ink-900)', marginBottom: 6 }}>
              {year}년도 {tab} 연간 예산 등록
            </div>
            <div style={{ fontSize: 13, color: 'var(--ink-500)', marginBottom: 24 }}>
              연간 예산을 설정합니다.
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 16 }}>
              {[
                { label: '시급 (원)', value: budgetHourlyWage, set: setBudgetHourlyWage },
                { label: '참여 예정 어르신 수 (명)', value: budgetSeniorCount, set: setBudgetSeniorCount },
                { label: '어르신 임금 예산 (원)', value: budgetWage, set: setBudgetWage },
                { label: '담당자 임금 예산 (원)', value: budgetMgr,  set: setBudgetMgr  },
                { label: '사업진행비 예산 (원)',   value: budgetOp,   set: setBudgetOp   },
              ].map((f) => (
                <div key={f.label}>
                  <div style={labelStyle}>{f.label}</div>
                  <input type="number" value={f.value} onChange={(e) => f.set(e.target.value)} placeholder="0" style={inputStyle}/>
                </div>
              ))}
            </div>

            {/* 총사업비 자동계산 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'var(--cream-50)', borderRadius: 10, marginBottom: 14 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-700)' }}>총 사업비 (자동 계산)</span>
              <span className="num" style={{ fontSize: 16, fontWeight: 800, color: 'var(--ink-900)' }}>{fmt(totalBudgetForm)}원</span>
            </div>

            {/* 어르신 임금 예산 검증 */}
            {canValidateWage && (
              <div style={{
                padding: '12px 16px', borderRadius: 10, marginBottom: 16, fontSize: 13, lineHeight: 1.5,
                background: wageMismatch ? '#FBE3E3' : 'var(--green-50)',
                border: `1px solid ${wageMismatch ? '#EBBCBC' : 'var(--green-200)'}`,
                color: wageMismatch ? 'var(--danger)' : 'var(--green-700)',
              }}>
                {wageMismatch ? (
                  <>
                    ⚠️ <strong>어르신 임금 예산 불일치</strong><br/>
                    시급 {fmt(hourlyNum)}원 × {annualHours}시간 × {seniorCountNum}명 = <strong>{fmt(expectedWage)}원</strong>이어야 합니다.
                    (입력: {fmt(wageNum)}원) — 금액을 맞춰야 저장할 수 있습니다.
                  </>
                ) : (
                  <>✓ 어르신 임금 예산이 시급·인원·연간시간 계산과 일치합니다.</>
                )}
              </div>
            )}

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <Button variant="secondary" size="md" onClick={() => setShowBudgetModal(false)}>취소</Button>
              <Button variant="primary" size="md" icon={<Icons.plus/>} onClick={handleCreateBudget} disabled={budgetSubmitting || wageMismatch}>
                {budgetSubmitting ? '등록 중…' : '등록'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

const labelStyle: React.CSSProperties = {
  fontSize: 13, fontWeight: 700, color: 'var(--ink-700)', marginBottom: 6,
};

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 12px', border: '1.5px solid var(--line)',
  borderRadius: 10, fontSize: 14, outline: 'none', background: '#fff', color: 'var(--ink-900)',
  display: 'block', boxSizing: 'border-box', fontFamily: 'inherit',
};

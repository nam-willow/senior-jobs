import { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { useBusinessUnits } from '../../hooks/useBusinessUnits';
import { useBudget } from '../../hooks/useBudget';

interface YearEndBudgetModalProps {
  nextYear: number;
  currentYear: number;
  onComplete: () => void;
  onSkip: () => void;
}

interface BudgetForm {
  total_wage_budget: string;
  manager_wage_budget: string;
  operation_budget: string;
}

const TYPE_LABEL: Record<string, string> = {
  public_benefit: '공익활동형', social_service: '사회서비스형', market: '시장형',
};

export function YearEndBudgetModal({ nextYear, currentYear, onComplete, onSkip }: YearEndBudgetModalProps) {
  const { units } = useBusinessUnits(nextYear);
  const [copyMode, setCopyMode] = useState<'copy' | 'manual'>('copy');
  const [forms, setForms] = useState<Record<string, BudgetForm>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // 현재 연도 첫 사업단 예산 (복사용 참고값)
  const firstUnit = units[0] ?? null;
  const { budget: currentBudget } = useBudget(firstUnit?.id ?? null, currentYear);

  useEffect(() => {
    if (units.length === 0) return;
    const init: Record<string, BudgetForm> = {};
    units.forEach((u) => {
      init[u.id] = {
        total_wage_budget: currentBudget ? String(currentBudget.total_wage_budget) : '',
        manager_wage_budget: currentBudget ? String(currentBudget.manager_wage_budget) : '',
        operation_budget: currentBudget ? String(currentBudget.operation_budget) : '',
      };
    });
    setForms(init);
  }, [units, currentBudget]);

  const setField = (buId: string, field: keyof BudgetForm, val: string) => {
    setForms((p) => ({ ...p, [buId]: { ...p[buId], [field]: val } }));
  };

  const handleSubmit = async () => {
    setError('');
    if (copyMode === 'manual') {
      for (const u of units) {
        const f = forms[u.id];
        if (!f?.total_wage_budget || !f?.manager_wage_budget || !f?.operation_budget) {
          setError('모든 항목을 입력해주세요.'); return;
        }
      }
    }
    setSaving(true);
    try {
      for (const u of units) {
        const f = forms[u.id];
        await api.post('/budgets/', {
          business_unit_id: u.id,
          year: nextYear,
          total_wage_budget: Number(f?.total_wage_budget ?? 0),
          manager_wage_budget: Number(f?.manager_wage_budget ?? 0),
          operation_budget: Number(f?.operation_budget ?? 0),
          senior_count: 0,
        });
      }
      onComplete();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? '저장 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const fmtWon = (v: string) => {
    const n = Number(v);
    if (!n) return '—';
    return n.toLocaleString() + '원';
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000, padding: 24,
    }}>
      <div style={{
        background: '#fff', borderRadius: 24, width: '100%', maxWidth: 540,
        boxShadow: 'var(--shadow-lg)', overflow: 'hidden',
      }}>
        {/* 헤더 */}
        <div style={{ background: 'var(--green-700)', color: '#fff', padding: '24px 32px 18px' }}>
          <div style={{ fontSize: 20, fontWeight: 800 }}>{nextYear}년도 사업비 등록</div>
          <div style={{ fontSize: 13, opacity: 0.85, marginTop: 4 }}>
            {nextYear}년도 탭을 이용하려면 새 사업비를 등록해주세요.
          </div>
        </div>

        {/* 복사 vs 직접 입력 선택 */}
        <div style={{ padding: '20px 32px 0', display: 'flex', gap: 10 }}>
          {([['copy', `${currentYear}년 금액 그대로 복사`], ['manual', '직접 입력']] as [string, string][]).map(([v, l]) => (
            <div key={v} onClick={() => setCopyMode(v as 'copy' | 'manual')} style={{
              flex: 1, padding: '12px', borderRadius: 12, textAlign: 'center',
              cursor: 'pointer', fontSize: 14, fontWeight: copyMode === v ? 700 : 500,
              border: `2px solid ${copyMode === v ? 'var(--green-600)' : 'var(--line)'}`,
              background: copyMode === v ? 'var(--green-50)' : '#fff',
              color: copyMode === v ? 'var(--green-700)' : 'var(--ink-500)',
            }}>
              {copyMode === v && '✓ '}{l}
            </div>
          ))}
        </div>

        {/* 본문 */}
        <div style={{ padding: '20px 32px', maxHeight: '50vh', overflowY: 'auto' }}>
          {copyMode === 'copy' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {units.map((u) => {
                const f = forms[u.id];
                return (
                  <div key={u.id} style={{
                    padding: '14px 18px', border: '1px solid var(--line)', borderRadius: 12,
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}>
                    <span style={{ fontWeight: 700, color: 'var(--ink-900)' }}>{TYPE_LABEL[u.type] ?? u.type}</span>
                    <div style={{ fontSize: 13, color: 'var(--ink-500)', textAlign: 'right' }}>
                      <div>임금 {fmtWon(f?.total_wage_budget ?? '')}</div>
                      <div>담당자 {fmtWon(f?.manager_wage_budget ?? '')}</div>
                      <div>사업비 {fmtWon(f?.operation_budget ?? '')}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            units.map((u) => (
              <div key={u.id} style={{ marginBottom: 20, padding: '16px 18px', border: '1px solid var(--line)', borderRadius: 12 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-900)', marginBottom: 12 }}>
                  {TYPE_LABEL[u.type] ?? u.type}
                </div>
                {([
                  ['total_wage_budget', '어르신 임금 예산'],
                  ['manager_wage_budget', '담당자 임금 예산'],
                  ['operation_budget', '사업진행비 예산'],
                ] as [keyof BudgetForm, string][]).map(([field, label]) => (
                  <div key={field} style={{ marginBottom: 10 }}>
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-500)', marginBottom: 4, display: 'block' }}>{label} (원)</label>
                    <input
                      type="number" value={forms[u.id]?.[field] ?? ''}
                      onChange={(e) => setField(u.id, field, e.target.value)}
                      placeholder="0"
                      style={{ width: '100%', padding: '9px 12px', border: '1.5px solid var(--line)', borderRadius: 8, fontSize: 14, outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box' }}
                    />
                  </div>
                ))}
              </div>
            ))
          )}
          {error && (
            <div style={{ background: '#FBE3E3', border: '1px solid var(--danger)', borderRadius: 8, padding: '10px 14px', fontSize: 13, color: 'var(--danger)', marginTop: 8 }}>
              {error}
            </div>
          )}
        </div>

        {/* 푸터 */}
        <div style={{ padding: '14px 32px 24px', borderTop: '1px solid var(--line-soft)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span onClick={onSkip} style={{ fontSize: 14, color: 'var(--ink-400)', cursor: 'pointer' }}>나중에 등록</span>
          <button onClick={handleSubmit} disabled={saving} style={{
            background: 'var(--green-700)', color: '#fff', border: 'none',
            borderRadius: 12, padding: '12px 28px', fontSize: 15, fontWeight: 700,
            cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.7 : 1, fontFamily: 'inherit',
          }}>
            {saving ? '저장 중…' : `${nextYear}년 사업비 등록`}
          </button>
        </div>
      </div>
    </div>
  );
}

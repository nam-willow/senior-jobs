import { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { useBusinessUnits } from '../../hooks/useBusinessUnits';
import { useAppStore } from '../../stores/appStore';

interface BudgetForm {
  total_wage_budget: string;
  manager_wage_budget: string;
  operation_budget: string;
}

const empty = (): BudgetForm => ({
  total_wage_budget: '',
  manager_wage_budget: '',
  operation_budget: '',
});

export function OnboardingModal({ onComplete }: { onComplete: () => void }) {
  const year = useAppStore((s) => s.year);
  const { units, loading: uLoading } = useBusinessUnits(year);
  const [forms, setForms] = useState<Record<string, BudgetForm>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (units.length > 0) {
      const init: Record<string, BudgetForm> = {};
      units.forEach((u) => { init[u.id] = empty(); });
      setForms(init);
    }
  }, [units]);

  const setField = (buId: string, field: keyof BudgetForm, val: string) => {
    setForms((p) => ({ ...p, [buId]: { ...p[buId], [field]: val } }));
  };

  const handleSubmit = async () => {
    setError('');
    for (const u of units) {
      const f = forms[u.id];
      if (!f) continue;
      if (!f.total_wage_budget || !f.manager_wage_budget || !f.operation_budget) {
        setError('모든 사업단의 예산을 입력해주세요.');
        return;
      }
    }
    setSaving(true);
    try {
      for (const u of units) {
        const f = forms[u.id];
        await api.post('/budgets/', {
          business_unit_id: u.id,
          year,
          total_wage_budget: Number(f.total_wage_budget.replace(/,/g, '')),
          manager_wage_budget: Number(f.manager_wage_budget.replace(/,/g, '')),
          operation_budget: Number(f.operation_budget.replace(/,/g, '')),
          senior_count: 0,
        });
      }
      onComplete();
    } catch (err: any) {
      const d = err?.response?.data?.detail;
      setError(typeof d === 'string' ? d : '저장 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const TYPE_LABEL: Record<string, string> = {
    public_benefit: '공익활동형', social_service: '사회서비스형', market: '시장형',
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000, padding: 24,
    }}>
      <div style={{
        background: '#fff', borderRadius: 24, width: '100%', maxWidth: 560,
        boxShadow: 'var(--shadow-lg)', overflow: 'hidden',
      }}>
        {/* 헤더 */}
        <div style={{
          background: 'var(--green-700)', color: '#fff',
          padding: '28px 32px 20px',
        }}>
          <div style={{ fontSize: 22, fontWeight: 800 }}>사업비를 등록해주세요</div>
          <div style={{ fontSize: 14, opacity: 0.85, marginTop: 6 }}>
            운영을 시작하려면 {year}년도 각 사업단의 예산을 입력해야 합니다.
          </div>
        </div>

        {/* 본문 */}
        <div style={{ padding: '24px 32px', maxHeight: '60vh', overflowY: 'auto' }}>
          {uLoading ? (
            <div style={{ textAlign: 'center', padding: 32, color: 'var(--ink-400)' }}>로딩 중…</div>
          ) : units.map((u) => (
            <div key={u.id} style={{
              marginBottom: 24, padding: '18px 20px',
              border: '1px solid var(--line)', borderRadius: 16,
            }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink-900)', marginBottom: 14 }}>
                {TYPE_LABEL[u.type] ?? u.type}
              </div>
              {([
                ['total_wage_budget', '어르신 임금 예산'],
                ['manager_wage_budget', '담당자 임금 예산'],
                ['operation_budget', '사업진행비 예산'],
              ] as [keyof BudgetForm, string][]).map(([field, label]) => (
                <div key={field} style={{ marginBottom: 12 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-500)', marginBottom: 4, display: 'block' }}>
                    {label} (원)
                  </label>
                  <input
                    type="number"
                    value={forms[u.id]?.[field] ?? ''}
                    onChange={(e) => setField(u.id, field, e.target.value)}
                    placeholder="0"
                    style={{
                      width: '100%', padding: '10px 12px', border: '1.5px solid var(--line)',
                      borderRadius: 8, fontSize: 15, outline: 'none',
                      fontFamily: 'inherit', boxSizing: 'border-box',
                    }}
                  />
                </div>
              ))}
            </div>
          ))}

          {error && (
            <div style={{
              background: '#FBE3E3', border: '1px solid var(--danger)',
              borderRadius: 8, padding: '10px 14px', fontSize: 13, color: 'var(--danger)',
              marginTop: 8,
            }}>
              {error}
            </div>
          )}
        </div>

        {/* 푸터 */}
        <div style={{
          padding: '16px 32px 24px', borderTop: '1px solid var(--line-soft)',
          display: 'flex', justifyContent: 'flex-end',
        }}>
          <button onClick={handleSubmit} disabled={saving} style={{
            background: 'var(--green-700)', color: '#fff', border: 'none',
            borderRadius: 12, padding: '13px 32px', fontSize: 16, fontWeight: 700,
            cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.7 : 1,
            fontFamily: 'inherit',
          }}>
            {saving ? '저장 중…' : '등록 완료 → 대시보드'}
          </button>
        </div>
      </div>
    </div>
  );
}

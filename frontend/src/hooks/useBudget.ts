import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

export interface AnnualBudget {
  id: string;
  business_unit_id: string;
  year: number;
  total_wage_budget: number;
  manager_wage_budget: number;
  operation_budget: number;
  senior_count: number;
  hourly_wage: number;
}

export interface Expenditure {
  id: string;
  annual_budget_id: string;
  category: 'wage' | 'manager_wage' | 'operation';
  item_name: string;
  amount: number;
  expense_date: string;
  note: string | null;
}

// 지출 내역 표시용 통합 행. 어르신 임금은 근무기록에서 자동 집계되므로 삭제 불가(deletable=false).
export interface ExpenseRow {
  id: string;
  source: 'work_record' | 'expenditure';
  category: 'wage' | 'manager_wage' | 'operation';
  item_name: string;
  amount: number;
  expense_date: string;   // 정렬용 (YYYY-MM-DD)
  display_date: string;   // 표시용 (어르신임금=YYYY.MM 월 단위, 수동=YYYY.MM.DD)
  note: string | null;
  deletable: boolean;
}

interface ApprovedWorkRecord {
  id: string;
  senior_name: string | null;
  year: number;
  month: number;
  worked_hours: number;
  amount_paid: number;
}

export function useBudget(buType: string | null, year: number) {
  const [budget, setBudget] = useState<AnnualBudget | null>(null);
  // 담당자 임금 / 사업진행비: 수동 등록 지출
  const [manualExpenditures, setManualExpenditures] = useState<Expenditure[]>([]);
  // 어르신 임금: 승인(APPROVED)된 근무기록에서 자동 집계
  const [wageRows, setWageRows] = useState<ExpenseRow[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(() => {
    if (!buType) { setBudget(null); setManualExpenditures([]); setWageRows([]); return; }
    setLoading(true);
    api.get<AnnualBudget>(`/budgets/by-type/${buType}/${year}`)
      .then(async (r) => {
        setBudget(r.data);
        // 어르신 임금: 승인된 근무기록을 월별(1일~말일)로 합산해 한 줄로 집계.
        // 같은 달에 추가로 승인되면(1차·2차) 같은 월 행에 자동 합산된다.
        try {
          const wr = await api.get<{ items: ApprovedWorkRecord[] }>('/work-records/', {
            params: { business_unit_id: r.data.business_unit_id, year, record_status: 'APPROVED', limit: 500 },
          });
          const byMonth = new Map<number, { total: number; count: number }>();
          (wr.data.items ?? []).forEach((rec) => {
            const agg = byMonth.get(rec.month) ?? { total: 0, count: 0 };
            agg.total += rec.amount_paid;
            agg.count += 1;
            byMonth.set(rec.month, agg);
          });
          const rows: ExpenseRow[] = [...byMonth.entries()].map(([month, agg]) => {
            const mm = String(month).padStart(2, '0');
            return {
              id: `wage-${year}-${mm}`,
              source: 'work_record' as const,
              category: 'wage' as const,
              item_name: `${month}월 임금`,
              amount: agg.total,
              expense_date: `${year}-${mm}-01`,
              display_date: `${year}.${mm}`,
              note: `어르신 ${agg.count}명`,
              deletable: false,
            };
          });
          setWageRows(rows);
        } catch {
          setWageRows([]);
        }
        // 한쪽 실패가 예산 표시를 무효화하지 않도록 분리한다. wage 카테고리 수동 지출은 자동 집계로 대체되어 제외.
        try {
          const exps = await api.get<{ items: Expenditure[] }>(`/budgets/expenditures/${r.data.id}`);
          setManualExpenditures((exps.data.items ?? []).filter((e) => e.category !== 'wage'));
        } catch {
          setManualExpenditures([]);
        }
      })
      .catch(() => { setBudget(null); setManualExpenditures([]); setWageRows([]); })
      .finally(() => setLoading(false));
  }, [buType, year]);

  useEffect(() => { fetch(); }, [fetch]);

  const manualRows: ExpenseRow[] = manualExpenditures.map((e) => ({
    id: e.id,
    source: 'expenditure',
    category: e.category,
    item_name: e.item_name,
    amount: e.amount,
    expense_date: e.expense_date,
    display_date: e.expense_date.slice(0, 10).replace(/-/g, '.'),
    note: e.note,
    deletable: true,
  }));

  // 지출 내역 통합 (어르신 임금 자동 + 수동 지출), 최신순 정렬
  const expenseRows: ExpenseRow[] = [...wageRows, ...manualRows].sort(
    (a, b) => b.expense_date.localeCompare(a.expense_date),
  );

  const wageSpent = wageRows.reduce((s, e) => s + e.amount, 0);

  const totalBudget = budget ? budget.total_wage_budget + budget.manager_wage_budget + budget.operation_budget : 0;
  const spentByCategory = (cat: string) =>
    expenseRows.filter((e) => e.category === cat).reduce((s, e) => s + e.amount, 0);
  const totalSpent = expenseRows.reduce((s, e) => s + e.amount, 0);
  const remaining = totalBudget - totalSpent;
  const pct = totalBudget > 0 ? Math.round(totalSpent / totalBudget * 100) : 0;

  return {
    budget, expenseRows, wageSpent, loading,
    totalBudget, totalSpent, remaining, pct, spentByCategory, refetch: fetch,
  };
}

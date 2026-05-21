import { useState, useEffect } from 'react';
import { api } from '../lib/api';

export interface AnnualBudget {
  id: string;
  business_unit_id: string;
  year: number;
  total_wage_budget: number;
  manager_wage_budget: number;
  operation_budget: number;
  senior_count: number;
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

export function useBudget(businessUnitId: string | null, year: number) {
  const [budget, setBudget] = useState<AnnualBudget | null>(null);
  const [expenditures, setExpenditures] = useState<Expenditure[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!businessUnitId) { setBudget(null); setExpenditures([]); return; }
    setLoading(true);
    api.get<AnnualBudget>(`/budgets/${businessUnitId}/${year}`)
      .then(async (r) => {
        setBudget(r.data);
        const exps = await api.get<{ items: Expenditure[] }>(`/budgets/expenditures/${r.data.id}`);
        setExpenditures(exps.data.items);
      })
      .catch(() => { setBudget(null); setExpenditures([]); })
      .finally(() => setLoading(false));
  }, [businessUnitId, year]);

  const totalBudget = budget ? budget.total_wage_budget + budget.manager_wage_budget + budget.operation_budget : 0;
  const spentByCategory = (cat: string) => expenditures.filter((e) => e.category === cat).reduce((s, e) => s + e.amount, 0);
  const totalSpent = expenditures.reduce((s, e) => s + e.amount, 0);
  const remaining = totalBudget - totalSpent;
  const pct = totalBudget > 0 ? Math.round(totalSpent / totalBudget * 100) : 0;

  return { budget, expenditures, loading, totalBudget, totalSpent, remaining, pct, spentByCategory };
}

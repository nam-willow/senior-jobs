import { useState, useEffect } from 'react';
import { api } from '../lib/api';

export interface BudgetBreakdown {
  wage: { budget: number; spent: number; rate: number };
  manager_wage: { budget: number; spent: number; rate: number };
  operation: { budget: number; spent: number; rate: number };
}

export interface BudgetSummaryItem {
  type: string;
  type_label: string;
  total_budget: number;
  total_expenditure: number;
  remaining: number;
  achievement_rate: number;
  senior_count: number;
  breakdown: BudgetBreakdown;
}

export interface DashboardSummary {
  year: number;
  summary: BudgetSummaryItem[];
}

export function useDashboardSummary(year: number) {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get<DashboardSummary>('/dashboard/summary', { params: { year } })
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [year]);

  return { data, loading };
}

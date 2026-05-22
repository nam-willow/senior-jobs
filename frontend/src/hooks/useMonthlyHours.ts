import { useState, useEffect } from 'react';
import { api } from '../lib/api';

export interface MonthlyHoursRow {
  m: string;
  pub: number;
  svc: number;
  mkt: number;
}

export function useMonthlyHours(year: number) {
  const [monthly, setMonthly] = useState<MonthlyHoursRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get<{ year: number; monthly: MonthlyHoursRow[] }>('/dashboard/monthly-hours', { params: { year } })
      .then((r) => setMonthly(r.data.monthly))
      .catch(() => setMonthly([]))
      .finally(() => setLoading(false));
  }, [year]);

  return { monthly, loading };
}

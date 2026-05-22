import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { PageType, TabType } from '../types';

export interface ApiAlert {
  id: string;
  tone: 'danger' | 'warm' | 'gold' | 'info';
  title: string;
  meta: string;
  goto?: PageType;
  tab?: TabType;
}

export function useAlerts(year: number) {
  const [alerts, setAlerts] = useState<ApiAlert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get<{ alerts: ApiAlert[]; year: number }>('/dashboard/alerts', { params: { year } })
      .then((r) => setAlerts(r.data.alerts))
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false));
  }, [year]);

  return { alerts, loading };
}

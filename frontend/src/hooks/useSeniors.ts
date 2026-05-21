import { useState, useEffect } from 'react';
import { api } from '../lib/api';

export interface ApiSenior {
  id: string;
  name: string;
  birth_date: string;
  workplace: string;
  allocated_hours: number;
  hourly_wage: number;
  default_session_hours: number;
  business_unit_id: string;
  notes: string | null;
  is_active: boolean;
}

export function useSeniors(businessUnitId: string | null) {
  const [seniors, setSeniors] = useState<ApiSenior[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!businessUnitId) { setSeniors([]); return; }
    setLoading(true);
    api.get<{ items: ApiSenior[] }>('/seniors/', {
      params: { business_unit_id: businessUnitId, limit: 200 },
    })
      .then((r) => setSeniors(r.data.items.filter((s) => s.is_active)))
      .catch(() => setSeniors([]))
      .finally(() => setLoading(false));
  }, [businessUnitId]);

  return { seniors, loading };
}

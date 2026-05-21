import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

export interface WorkRecord {
  id: string;
  senior_id: string;
  year: number;
  month: number;
  worked_hours: number;
  session_count: number;
  amount_paid: number;
  status: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';
  reason_for_overtime: string | null;
  business_unit_id: string;
}

export function useWorkRecords(year: number, month: number, businessUnitId: string | null) {
  const [records, setRecords] = useState<WorkRecord[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(() => {
    if (!businessUnitId) { setRecords([]); return; }
    setLoading(true);
    api.get<{ items: WorkRecord[] }>('/work-records/', {
      params: { year, month, business_unit_id: businessUnitId, limit: 200 },
    })
      .then((r) => setRecords(r.data.items))
      .catch(() => setRecords([]))
      .finally(() => setLoading(false));
  }, [year, month, businessUnitId]);

  useEffect(() => { fetch(); }, [fetch]);

  const save = async (seniorId: string, hours: number, reason?: string) => {
    const existing = records.find((r) => r.senior_id === seniorId && r.status === 'DRAFT');
    if (existing) {
      await api.put(`/work-records/${existing.id}`, {
        worked_hours: hours,
        reason_for_overtime: reason ?? null,
      });
    } else {
      await api.post('/work-records/', {
        senior_id: seniorId,
        business_unit_id: businessUnitId,
        year,
        month,
        worked_hours: hours,
        session_count: Math.ceil(hours / 3),
        reason_for_overtime: reason ?? null,
      });
    }
    fetch();
  };

  return { records, loading, refetch: fetch, save };
}

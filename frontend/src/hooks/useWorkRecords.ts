import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

export interface WorkRecord {
  id: string;
  senior_id: string;
  year: number;
  month: number;
  worked_hours: number;
  worked_days: number;
  amount_paid: number;
  status: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';
  overtime_reason: string | null;
}

export interface SavePayload {
  hours: number;
  amount: number;
  workedDays: number;
  reason?: string;
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

  const save = async (seniorId: string, payload: SavePayload) => {
    const { hours, amount, workedDays, reason } = payload;
    const existing = records.find((r) => r.senior_id === seniorId && r.status === 'DRAFT');
    if (existing) {
      await api.put(`/work-records/${existing.id}`, {
        worked_hours: hours,
        worked_days: workedDays,
        amount_paid: amount,
        overtime_reason: reason ?? null,
      });
    } else {
      await api.post('/work-records/', {
        senior_id: seniorId,
        year,
        month,
        worked_hours: hours,
        worked_days: workedDays,
        amount_paid: amount,
        overtime_reason: reason ?? null,
      });
    }
    fetch();
  };

  const submit = async (recordId: string) => {
    await api.post(`/work-records/${recordId}/submit`);
    fetch();
  };

  return { records, loading, refetch: fetch, save, submit };
}

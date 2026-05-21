import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

export interface ConsultLog {
  id: string;
  senior_id: string;
  social_worker_id: string;
  consultation_date: string;
  method: 'phone' | 'visit' | 'in_person' | 'other';
  content: string;
  memo: string | null;
  default_session_hours: number;
  created_at: string;
}

const METHOD_LABEL: Record<string, string> = {
  phone: '전화', visit: '방문', in_person: '내방', other: '기타',
};

export function useConsultationLogs(seniorId?: string) {
  const [logs, setLogs] = useState<ConsultLog[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = { limit: '200' };
    if (seniorId) params.senior_id = seniorId;
    api.get<{ items: ConsultLog[] }>('/consultation-logs/', { params })
      .then((r) => setLogs(r.data.items))
      .catch(() => setLogs([]))
      .finally(() => setLoading(false));
  }, [seniorId]);

  useEffect(() => { fetch(); }, [fetch]);

  const create = async (payload: {
    senior_id: string;
    consultation_date: string;
    method: string;
    content: string;
    memo?: string;
    default_session_hours: number;
  }) => {
    await api.post('/consultation-logs/', payload);
    fetch();
  };

  return { logs, loading, refetch: fetch, create, methodLabel: METHOD_LABEL };
}

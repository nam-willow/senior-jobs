import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import type { TabType } from '../types';

export interface BusinessUnit {
  id: string;
  name: string;
  type: 'public_benefit' | 'social_service' | 'market';
  year: number;
  monthly_default_hours: number;
  monthly_max_hours: number;
  total_annual_hours: number;
  session_default_hours: number;
  allocated_hours: number;
  is_active: boolean;
}

const TYPE_MAP: Record<TabType, string> = {
  '공익활동형':   'public_benefit',
  '사회서비스형': 'social_service',
  '시장형':       'market',
};
const TYPE_REVERSE: Record<string, TabType> = {
  public_benefit:   '공익활동형',
  social_service:   '사회서비스형',
  market:           '시장형',
};

export function useBusinessUnits(year: number) {
  const [units, setUnits] = useState<BusinessUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  const fetchUnits = useCallback(() => {
    setLoading(true);
    api.get<{ items: BusinessUnit[] }>('/business-units/', { params: { year } })
      .then((r) => setUnits(r.data.items))
      .catch(() => setUnits([]))
      .finally(() => setLoading(false));
  }, [year, tick]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchUnits(); }, [fetchUnits]);

  const refetch = () => setTick((t) => t + 1);
  const byTab = (tab: TabType) => units.find((u) => u.type === TYPE_MAP[tab]) ?? null;
  const tabOf = (type: string): TabType => TYPE_REVERSE[type] ?? '공익활동형';

  return { units, loading, byTab, tabOf, refetch };
}

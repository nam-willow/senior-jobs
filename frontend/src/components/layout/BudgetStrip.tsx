import type { TabType } from '../../types';
import { useAppStore } from '../../stores/appStore';
import { useBusinessUnits } from '../../hooks/useBusinessUnits';
import { useBudget } from '../../hooks/useBudget';
import { Chip } from '../shared/Chip';
import { Progress } from '../shared/Progress';
import { TAB_TONE, fmt } from '../../data/mockData';

interface BudgetStripProps {
  tab: TabType;
}

export function BudgetStrip({ tab }: BudgetStripProps) {
  const year = useAppStore((s) => s.year);
  const { byTab } = useBusinessUnits(year);
  const bu = byTab(tab);
  const { budget, spentByCategory, loading } = useBudget(bu?.type ?? null, year);
  const color = TAB_TONE[tab].color;

  const lines = [
    { l: '어르신 임금', budget: budget?.total_wage_budget ?? 0,    spent: spentByCategory('wage') },
    { l: '담당자 임금', budget: budget?.manager_wage_budget ?? 0,   spent: spentByCategory('manager_wage') },
    { l: '사업진행비',  budget: budget?.operation_budget ?? 0,      spent: spentByCategory('operation') },
  ];

  if (loading) {
    return <div style={{ height: 88, background: 'var(--cream-50)', borderRadius: 14, marginBottom: 22, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-400)' }}>로딩 중…</div>;
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 22 }}>
      {lines.map((line) => {
        const empty = line.budget === 0;
        const pct = empty ? 0 : Math.min(Math.round(line.spent / line.budget * 100), 100);
        const danger = pct >= 100;
        return (
          <div key={line.l} style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 14, padding: '16px 18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-700)' }}>{line.l}</span>
              <Chip tone={empty ? 'neutral' : danger ? 'danger' : 'green'} size="sm">
                {empty ? '미배정' : `${pct}%`}
              </Chip>
            </div>
            <Progress value={pct} color={danger ? 'var(--danger)' : color} height={8}/>
            <div className="num" style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--ink-500)', marginTop: 6 }}>
              <span>사용 <strong style={{ color: empty ? 'var(--ink-400)' : color }}>{fmt(line.spent)}원</strong></span>
              <span>{empty ? '—' : `${fmt(line.budget)}원`}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

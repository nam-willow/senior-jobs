import type { TabType } from '../../types';
import { BUDGET, fmt } from '../../data/mockData';
import { Chip } from '../shared/Chip';
import { Progress } from '../shared/Progress';

interface BudgetStripProps {
  tab: TabType;
}

export function BudgetStrip({ tab }: BudgetStripProps) {
  const b = BUDGET[tab];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 22 }}>
      {b.lines.map((line) => {
        const empty = line.total === 0;
        const danger = line.pct >= 100;
        return (
          <div key={line.l} style={{
            background: '#fff', border: '1px solid var(--line)', borderRadius: 14,
            padding: '16px 18px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-700)' }}>{line.l}</span>
              <Chip tone={empty ? 'neutral' : danger ? 'danger' : 'green'} size="sm">
                {empty ? '미배정' : `${line.pct}%`}
              </Chip>
            </div>
            <Progress value={line.pct} color={danger ? 'var(--danger)' : b.color} height={8}/>
            <div className="num" style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--ink-500)', marginTop: 6 }}>
              <span>사용 <strong style={{ color: empty ? 'var(--ink-400)' : b.color }}>{fmt(line.used)}원</strong></span>
              <span>{empty ? '—' : `${fmt(line.total)}원`}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

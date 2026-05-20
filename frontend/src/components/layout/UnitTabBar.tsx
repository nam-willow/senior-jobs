import type { ReactNode } from 'react';
import type { TabType } from '../../types';
import { TABS, TAB_TONE } from '../../data/mockData';

interface UnitTabBarProps {
  tab: TabType;
  onChange: (t: TabType) => void;
  right?: ReactNode;
}

export function UnitTabBar({ tab, onChange, right }: UnitTabBarProps) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-end',
      borderBottom: '1.5px solid var(--line)', marginBottom: 24,
    }}>
      {TABS.map((t) => (
        <div key={t} onClick={() => onChange(t)} style={{
          padding: '14px 22px', fontSize: 16, fontWeight: tab === t ? 700 : 500,
          cursor: 'pointer', color: tab === t ? TAB_TONE[t].color : 'var(--ink-500)',
          borderBottom: tab === t ? `3px solid ${TAB_TONE[t].color}` : '3px solid transparent',
          marginBottom: -1.5, transition: 'color .15s',
        }}>{t}</div>
      ))}
      {right && (
        <div style={{ marginLeft: 'auto', paddingBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
          {right}
        </div>
      )}
    </div>
  );
}

import type { ReactNode } from 'react';

type AlertTone = 'info' | 'warn' | 'danger' | 'gold';

const STYLES: Record<AlertTone, { bg: string; fg: string; bd: string; emoji: string }> = {
  info:   { bg: '#DFEBF1',          fg: '#1F4E63', bd: '#B9D2DE', emoji: 'ℹ️' },
  warn:   { bg: 'var(--warm-soft)', fg: '#9B4221', bd: '#EBB89A', emoji: '⚠️' },
  danger: { bg: '#FBE3E3',          fg: '#7A1F1F', bd: '#EBBCBC', emoji: '🚫' },
  gold:   { bg: 'var(--gold-soft)', fg: '#7A5B17', bd: '#E7CF8B', emoji: '💡' },
};

interface AlertBoxProps {
  tone?: AlertTone;
  children: ReactNode;
}

export function AlertBox({ tone = 'info', children }: AlertBoxProps) {
  const s = STYLES[tone];
  return (
    <div style={{
      display: 'flex', gap: 12, alignItems: 'flex-start',
      padding: '14px 18px', background: s.bg, color: s.fg,
      border: `1px solid ${s.bd}`, borderRadius: 12,
      fontSize: 14, marginBottom: 18,
    }}>
      <span style={{ fontSize: 18, lineHeight: 1, marginTop: 1 }}>{s.emoji}</span>
      <div style={{ lineHeight: 1.55 }}>{children}</div>
    </div>
  );
}

import type { ChipTone } from '../../types';

const CHIP_STYLES: Record<ChipTone, { bg: string; color: string }> = {
  green:   { bg: 'var(--green-100)',  color: 'var(--green-800)' },
  info:    { bg: '#DBEEFF',           color: '#1E4D70'          },
  warm:    { bg: 'var(--warm-soft)',  color: '#7A3A22'          },
  gold:    { bg: 'var(--gold-soft)',  color: '#7A5B17'          },
  danger:  { bg: '#FBE3E3',           color: '#7A1F1F'          },
  neutral: { bg: 'var(--cream-100)',  color: 'var(--ink-700)'   },
};

interface ChipProps {
  tone?: ChipTone;
  size?: 'sm' | 'md';
  children: React.ReactNode;
}

export function Chip({ tone = 'neutral', size = 'md', children }: ChipProps) {
  const s = CHIP_STYLES[tone];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      background: s.bg, color: s.color,
      borderRadius: 999,
      padding: size === 'sm' ? '3px 10px' : '5px 14px',
      fontSize: size === 'sm' ? 12 : 13,
      fontWeight: 700, whiteSpace: 'nowrap',
    }}>
      {children}
    </span>
  );
}

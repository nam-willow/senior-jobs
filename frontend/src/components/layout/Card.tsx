import type { CSSProperties, ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  title?: string;
  right?: ReactNode;
  padding?: string;
  style?: CSSProperties;
}

export function Card({ children, title, right, padding = '24px', style = {} }: CardProps) {
  return (
    <div style={{
      background: '#fff', border: '1px solid var(--line)', borderRadius: 18,
      boxShadow: 'var(--shadow-sm)', overflow: 'hidden', ...style,
    }}>
      {title && (
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '18px 24px', borderBottom: '1px solid var(--line-soft)',
        }}>
          <div style={{ fontSize: 17, fontWeight: 800, color: 'var(--ink-900)' }}>{title}</div>
          {right}
        </div>
      )}
      <div style={{ padding }}>{children}</div>
    </div>
  );
}

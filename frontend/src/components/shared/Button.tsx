import type { ButtonVariant, ButtonSize } from '../../types';
import type { CSSProperties, ReactNode, MouseEventHandler } from 'react';

const VARIANTS: Record<ButtonVariant, CSSProperties> = {
  primary:   { background: 'var(--green-700)', color: '#fff', border: '1.5px solid var(--green-700)' },
  secondary: { background: '#fff', color: 'var(--green-700)', border: '1.5px solid var(--green-700)' },
  ghost:     { background: 'transparent', color: 'var(--ink-700)', border: '1.5px solid var(--line)' },
};

const SIZES: Record<ButtonSize, CSSProperties> = {
  sm: { padding: '8px 14px', fontSize: 13, borderRadius: 10 },
  md: { padding: '11px 18px', fontSize: 15, borderRadius: 12 },
  lg: { padding: '14px 24px', fontSize: 16, borderRadius: 14 },
};

interface ButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
  full?: boolean;
  disabled?: boolean;
  onClick?: MouseEventHandler<HTMLButtonElement>;
  children?: ReactNode;
}

export function Button({
  variant = 'ghost', size = 'md', icon, full, disabled, onClick, children,
}: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer',
        width: full ? '100%' : undefined,
        justifyContent: full ? 'center' : undefined,
        opacity: disabled ? 0.5 : 1,
        transition: 'opacity .15s',
        whiteSpace: 'nowrap',
        ...VARIANTS[variant],
        ...SIZES[size],
      }}
    >
      {icon}
      {children}
    </button>
  );
}

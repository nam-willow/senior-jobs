interface ProgressProps {
  value: number;
  color?: string;
  height?: number;
}

export function Progress({ value, color = 'var(--green-600)', height = 8 }: ProgressProps) {
  return (
    <div style={{ height, background: 'var(--line-soft)', borderRadius: height, overflow: 'hidden' }}>
      <div style={{
        width: `${Math.min(100, Math.max(0, value))}%`,
        height: '100%',
        background: color,
        borderRadius: height,
        transition: 'width .4s',
      }}/>
    </div>
  );
}

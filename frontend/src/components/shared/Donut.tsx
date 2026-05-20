interface DonutProps {
  value: number;
  color: string;
  size?: number;
  label?: string;
  sub?: string;
}

export function Donut({ value, color, size = 120, label, sub }: DonutProps) {
  const r = (size - 22) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(100, Math.max(0, value));
  const dash = (pct / 100) * circ;

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--line-soft)" strokeWidth={14}/>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth={14}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      }}>
        {label && <div className="num" style={{ fontSize: size > 100 ? 20 : 15, fontWeight: 800, color }}>{label}</div>}
        {sub && <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 2 }}>{sub}</div>}
      </div>
    </div>
  );
}

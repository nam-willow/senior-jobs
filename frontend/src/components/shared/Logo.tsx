export function Logo() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{
        width: 38, height: 38, borderRadius: 12,
        background: 'var(--green-700)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#fff', fontSize: 18, fontWeight: 900,
      }}>노</div>
      <div>
        <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--ink-900)', lineHeight: 1.1 }}>노인일자리</div>
        <div style={{ fontSize: 12, color: 'var(--ink-500)', lineHeight: 1.1 }}>관리 시스템</div>
      </div>
    </div>
  );
}

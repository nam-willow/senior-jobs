import { useState } from 'react';
import type { PageType } from '../types';
import { useConsultationLogs } from '../hooks/useConsultationLogs';
import { useSeniors } from '../hooks/useSeniors';
import { useBusinessUnits } from '../hooks/useBusinessUnits';
import { useAppStore } from '../stores/appStore';
import { Modal } from '../components/layout/Modal';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Button } from '../components/shared/Button';
import { Icons } from '../components/shared/Icons';

const METHOD_LABEL: Record<string, string> = {
  phone: '전화', visit: '방문', in_person: '내방', other: '기타',
};
const METHOD_OPTIONS = ['phone', 'visit', 'in_person', 'other'] as const;

interface ConsultProps {
  onNavigate: (page: PageType, seniorId?: number) => void;
}

export function Consult({ onNavigate: _onNavigate }: ConsultProps) {
  const year = useAppStore((s) => s.year);
  const { units, tabOf } = useBusinessUnits(year);
  const { logs, loading, create } = useConsultationLogs();
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState('전체');
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    senior_id: '',
    consultation_date: new Date().toISOString().slice(0, 16),
    method: 'phone' as string,
    content: '',
    memo: '',
    default_session_hours: 3,
  });

  const buId0 = units[0]?.id ?? null;
  const buId1 = units[1]?.id ?? null;
  const buId2 = units[2]?.id ?? null;
  const { seniors: s0 } = useSeniors(buId0);
  const { seniors: s1 } = useSeniors(buId1);
  const { seniors: s2 } = useSeniors(buId2);
  const allSeniors = [...s0, ...s1, ...s2];

  const seniorName = (id: string) => allSeniors.find((s) => s.id === id)?.name ?? '—';
  const seniorUnit = (id: string) => {
    const s = allSeniors.find((x) => x.id === id);
    if (!s) return null;
    const bu = units.find((u) => u.id === s.business_unit_id);
    return bu ? tabOf(bu.type) : null;
  };

  const filtered = logs.filter((c) => filter === '전체' || METHOD_LABEL[c.method] === filter);

  const handleSave = async () => {
    if (!form.senior_id || !form.content) return;
    setSaving(true);
    try {
      await create({
        senior_id: form.senior_id,
        consultation_date: form.consultation_date + ':00',
        method: form.method,
        content: form.content,
        memo: form.memo || undefined,
        default_session_hours: form.default_session_hours,
      });
      setOpen(false);
      setForm({ senior_id: '', consultation_date: new Date().toISOString().slice(0, 16), method: 'phone', content: '', memo: '', default_session_hours: 3 });
    } finally {
      setSaving(false);
    }
  };

  const stats = [
    { lb: '전체 상담',  val: `${logs.length}건`, color: 'var(--green-700)' },
    { lb: '전화 상담',  val: `${logs.filter((l) => l.method === 'phone').length}건`, color: 'var(--info)' },
    { lb: '방문 상담',  val: `${logs.filter((l) => l.method === 'visit').length}건`, color: 'var(--warm)' },
    { lb: '내방·기타', val: `${logs.filter((l) => l.method === 'in_person' || l.method === 'other').length}건`, color: 'var(--ink-700)' },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
        <div style={{ display: 'flex', gap: 6 }}>
          {['전체', '전화', '방문', '내방', '기타'].map((s) => (
            <div key={s} onClick={() => setFilter(s)} style={{
              padding: '10px 16px', borderRadius: 999, fontSize: 14, fontWeight: 600, cursor: 'pointer',
              background: filter === s ? 'var(--green-700)' : '#fff',
              color:      filter === s ? '#fff' : 'var(--ink-700)',
              border:     `1.5px solid ${filter === s ? 'var(--green-700)' : 'var(--line)'}`,
            }}>{s}</div>
          ))}
        </div>
        <Button variant="primary" size="sm" icon={<Icons.plus/>} onClick={() => setOpen(true)}>상담 등록</Button>
      </div>

      <div className="g4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 18 }}>
        {stats.map((s) => (
          <div key={s.lb} style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 18, padding: '16px 18px', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>{s.lb}</div>
            <div className="num" style={{ fontSize: 26, fontWeight: 800, color: s.color, marginTop: 4 }}>{s.val}</div>
          </div>
        ))}
      </div>

      <Card title={`상담 기록 (${filtered.length}건)`} padding="0">
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)' }}>로딩 중…</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
            <thead>
              <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
                {['상담일시', '어르신', '사업단', '방법', '상담 내용', ''].map((h) => (
                  <th key={h} style={{ padding: '14px 18px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => {
                const unit = seniorUnit(c.senior_id);
                const chipTone = unit === '공익활동형' ? 'green' : unit === '사회서비스형' ? 'info' : 'warm';
                return (
                  <tr key={c.id} style={{ borderTop: '1px solid var(--line-soft)' }}>
                    <td style={{ padding: '14px 18px' }}>
                      <div className="num" style={{ fontSize: 15, fontWeight: 700 }}>{c.consultation_date.slice(0, 10).replace(/-/g, '.')}</div>
                      <div className="num" style={{ fontSize: 13, color: 'var(--ink-500)' }}>{c.consultation_date.slice(11, 16)}</div>
                    </td>
                    <td style={{ padding: '14px 18px', fontSize: 16, fontWeight: 700, color: 'var(--green-700)' }}>{seniorName(c.senior_id)}</td>
                    <td style={{ padding: '14px 18px' }}>
                      {unit && <Chip tone={chipTone as 'green' | 'info' | 'warm'} size="sm">{unit}</Chip>}
                    </td>
                    <td style={{ padding: '14px 18px' }}>
                      <Chip tone="green" size="sm">{METHOD_LABEL[c.method] ?? c.method}</Chip>
                    </td>
                    <td style={{ padding: '14px 18px', color: 'var(--ink-700)', maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.content}</td>
                    <td style={{ padding: '14px 18px' }}><Button variant="ghost" size="sm">수정</Button></td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr><td colSpan={6} style={{ padding: 48, textAlign: 'center', color: 'var(--ink-400)' }}>상담 기록이 없습니다.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} width={620}>
        <div style={{ padding: '28px 32px', borderBottom: '1px solid var(--line)' }}>
          <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--ink-900)' }}>새 상담 등록</div>
        </div>
        <div style={{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Field label="어르신 선택">
            <select value={form.senior_id} onChange={(e) => setForm({ ...form, senior_id: e.target.value })} style={inputStyle}>
              <option value="">어르신을 선택하세요</option>
              {allSeniors.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="상담일시">
            <input type="datetime-local" value={form.consultation_date}
              onChange={(e) => setForm({ ...form, consultation_date: e.target.value })} style={inputStyle}/>
          </Field>
          <Field label="상담 방법">
            <div style={{ display: 'flex', gap: 8 }}>
              {METHOD_OPTIONS.map((m) => (
                <div key={m} onClick={() => setForm({ ...form, method: m })} style={{
                  padding: '8px 16px', borderRadius: 999, fontSize: 14, fontWeight: 600, cursor: 'pointer',
                  background: form.method === m ? 'var(--green-700)' : '#fff',
                  color: form.method === m ? '#fff' : 'var(--ink-700)',
                  border: `1.5px solid ${form.method === m ? 'var(--green-700)' : 'var(--line)'}`,
                }}>{METHOD_LABEL[m]}</div>
              ))}
            </div>
          </Field>
          <Field label="상담 내용">
            <textarea value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })}
              style={{ ...inputStyle, minHeight: 100 }} rows={4} placeholder="상담 내용을 자세히 기록하세요."/>
          </Field>
          <Field label="메모 (선택)">
            <textarea value={form.memo} onChange={(e) => setForm({ ...form, memo: e.target.value })}
              style={{ ...inputStyle, minHeight: 60 }} rows={2} placeholder="기타 메모"/>
          </Field>
        </div>
        <div style={{ padding: '20px 32px', borderTop: '1px solid var(--line)', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <Button variant="ghost" size="md" onClick={() => setOpen(false)}>취소</Button>
          <Button variant="primary" size="md" icon={<Icons.check/>} onClick={handleSave}>
            {saving ? '저장 중…' : '저장'}
          </Button>
        </div>
      </Modal>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-700)', marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '12px 14px', border: '1.5px solid var(--line)',
  borderRadius: 10, fontSize: 15, outline: 'none', background: '#fff', color: 'var(--ink-900)',
  display: 'block', boxSizing: 'border-box', fontFamily: 'inherit',
};

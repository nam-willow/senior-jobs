import { useState, useEffect, useCallback } from 'react';
import { TAB_TONE } from '../data/mockData';
import type { TabType } from '../types';
import { useAppStore } from '../stores/appStore';
import { api } from '../lib/api';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Button } from '../components/shared/Button';
import { Icons } from '../components/shared/Icons';

interface WorkRecordItem {
  id: string;
  senior_id: string;
  senior_name?: string;
  business_unit_type?: string;
  business_unit_name?: string;
  year: number;
  month: number;
  worked_hours: number;
  amount_paid: number;
  status: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';
  reject_reason?: string;
  submitted_at?: string;
  approved_at?: string;
}

const STATUS_KO: Record<string, string> = {
  SUBMITTED: '대기중',
  APPROVED: '승인',
  REJECTED: '반려',
  DRAFT: '임시저장',
};

const TYPE_KO: Record<string, TabType> = {
  public_benefit: '공익활동형',
  social_service: '사회서비스형',
  market: '시장형',
};

export function Approvals() {
  const year = useAppStore((s) => s.year);
  const month = useAppStore((s) => s.month);
  const [filter, setFilter] = useState<'SUBMITTED' | 'APPROVED' | 'REJECTED' | 'ALL'>('SUBMITTED');
  const [records, setRecords] = useState<WorkRecordItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [rejectModal, setRejectModal] = useState<{ id: string; name: string } | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchRecords = useCallback(() => {
    setLoading(true);
    const params: Record<string, string | number> = { year, month, limit: 200 };
    if (filter !== 'ALL') params.record_status = filter;
    api.get<{ items: WorkRecordItem[] }>('/work-records/', { params })
      .then((r) => setRecords(r.data.items))
      .catch(() => setRecords([]))
      .finally(() => setLoading(false));
  }, [year, month, filter]);

  useEffect(() => { fetchRecords(); }, [fetchRecords]);

  const counts = {
    SUBMITTED: records.filter((r) => r.status === 'SUBMITTED').length,
    APPROVED:  records.filter((r) => r.status === 'APPROVED').length,
    REJECTED:  records.filter((r) => r.status === 'REJECTED').length,
  };

  const filtered = filter === 'ALL' ? records : records.filter((r) => r.status === filter);

  const handleApprove = async (id: string) => {
    setActionLoading(true);
    try {
      await api.post(`/work-records/${id}/approve`);
      fetchRecords();
    } catch {
      alert('승인 처리 중 오류가 발생했습니다.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!rejectModal || !rejectReason.trim()) return;
    setActionLoading(true);
    try {
      await api.post(`/work-records/${rejectModal.id}/reject`, { reject_reason: rejectReason });
      setRejectModal(null);
      setRejectReason('');
      fetchRecords();
    } catch {
      alert('반려 처리 중 오류가 발생했습니다.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <>
      <div style={{ display: 'flex', gap: 14, marginBottom: 20 }}>
        {[
          { key: 'ALL',       label: '전체',  val: records.length,       color: 'var(--ink-900)' },
          { key: 'SUBMITTED', label: '대기중', val: counts['SUBMITTED'], color: 'var(--warm)'    },
          { key: 'APPROVED',  label: '승인',   val: counts['APPROVED'],  color: 'var(--green-700)' },
          { key: 'REJECTED',  label: '반려',   val: counts['REJECTED'],  color: 'var(--danger)'  },
        ].map((s) => (
          <div key={s.key} onClick={() => setFilter(s.key as typeof filter)} style={{
            flex: 1, padding: '20px 24px', background: '#fff',
            border: `1.5px solid ${filter === s.key ? s.color : 'var(--line)'}`,
            borderRadius: 16, cursor: 'pointer',
            boxShadow: filter === s.key ? 'var(--shadow)' : 'var(--shadow-sm)',
          }}>
            <div style={{ fontSize: 14, color: 'var(--ink-500)', fontWeight: 600 }}>{s.label}</div>
            <div className="num" style={{ fontSize: 32, fontWeight: 800, color: s.color, marginTop: 6 }}>
              {s.val}<span style={{ fontSize: 16, color: 'var(--ink-500)', marginLeft: 4 }}>건</span>
            </div>
          </div>
        ))}
      </div>

      <Card title={`결재 목록 — ${year}년 ${month}월`} padding="0">
        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: 'var(--ink-400)' }}>로딩 중…</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
            <thead>
              <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
                {['어르신', '사업단', '연월', '근무시간', '지급금액', '상태', '결재'].map((h) => (
                  <th key={h} style={{ padding: '14px 18px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={7} style={{ padding: 48, textAlign: 'center', color: 'var(--ink-400)' }}>결재 대기 건이 없습니다.</td></tr>
              )}
              {filtered.map((a) => {
                const tabType = TYPE_KO[a.business_unit_type ?? ''] ?? '공익활동형';
                const statusKo = STATUS_KO[a.status] ?? a.status;
                return (
                  <tr key={a.id} style={{ borderTop: '1px solid var(--line-soft)', background: a.status === 'SUBMITTED' ? 'var(--cream-50)' : '#fff' }}>
                    <td style={{ padding: '16px 18px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        {a.status === 'SUBMITTED' && <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--warm)', display: 'inline-block' }}/>}
                        <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink-900)' }}>{a.senior_name ?? '—'}</span>
                      </div>
                    </td>
                    <td style={{ padding: '16px 18px' }}>
                      <Chip tone={TAB_TONE[tabType].chip as 'green'|'info'|'warm'} size="sm">{tabType}</Chip>
                    </td>
                    <td className="num" style={{ padding: '16px 18px', color: 'var(--ink-700)' }}>{a.year}.{String(a.month).padStart(2, '0')}</td>
                    <td className="num" style={{ padding: '16px 18px', fontWeight: 600 }}>{a.worked_hours}h</td>
                    <td className="num" style={{ padding: '16px 18px', fontWeight: 700, color: a.amount_paid ? 'var(--ink-900)' : 'var(--ink-400)' }}>
                      {a.amount_paid ? a.amount_paid.toLocaleString('ko-KR') + '원' : '—'}
                    </td>
                    <td style={{ padding: '16px 18px' }}>
                      <Chip tone={a.status === 'APPROVED' ? 'green' : a.status === 'REJECTED' ? 'danger' : 'warm'} size="sm">{statusKo}</Chip>
                      {a.status === 'REJECTED' && a.reject_reason && (
                        <div style={{ fontSize: 11, color: 'var(--danger)', marginTop: 4, maxWidth: 180 }}>{a.reject_reason}</div>
                      )}
                    </td>
                    <td style={{ padding: '16px 18px' }}>
                      {a.status === 'SUBMITTED' ? (
                        <div style={{ display: 'flex', gap: 6 }}>
                          <Button variant="primary" size="sm" icon={<Icons.check/>}
                            onClick={() => handleApprove(a.id)}>
                            {actionLoading ? '…' : '승인'}
                          </Button>
                          <Button variant="ghost" size="sm"
                            onClick={() => { setRejectModal({ id: a.id, name: a.senior_name ?? '—' }); setRejectReason(''); }}>
                            반려
                          </Button>
                        </div>
                      ) : (
                        <span style={{ fontSize: 13, color: 'var(--ink-400)' }}>처리 완료</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>

      {/* Reject reason modal */}
      {rejectModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200,
        }} onClick={() => setRejectModal(null)}>
          <div onClick={(e) => e.stopPropagation()} style={{
            background: '#fff', borderRadius: 20, padding: '28px 32px', width: 420,
            boxShadow: '0 8px 40px rgba(0,0,0,0.18)',
          }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--ink-900)', marginBottom: 8 }}>
              반려 — {rejectModal.name}
            </div>
            <div style={{ fontSize: 14, color: 'var(--ink-500)', marginBottom: 16 }}>반려 사유를 입력해주세요.</div>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="예: 영수증 누락 — 보완 후 재제출"
              rows={4}
              style={{ width: '100%', padding: '12px 14px', border: '1.5px solid var(--line)', borderRadius: 10, fontSize: 14, outline: 'none', resize: 'vertical', boxSizing: 'border-box' }}
            />
            <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
              <button onClick={() => setRejectModal(null)} style={{
                flex: 1, padding: '12px 0', borderRadius: 12, border: '1.5px solid var(--line)',
                background: '#fff', fontSize: 15, fontWeight: 600, cursor: 'pointer', color: 'var(--ink-700)',
              }}>취소</button>
              <button onClick={handleReject} disabled={!rejectReason.trim() || actionLoading} style={{
                flex: 2, padding: '12px 0', borderRadius: 12, border: 'none',
                background: rejectReason.trim() ? 'var(--danger)' : 'var(--line)',
                fontSize: 15, fontWeight: 700, cursor: rejectReason.trim() ? 'pointer' : 'not-allowed', color: '#fff',
              }}>반려 처리</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

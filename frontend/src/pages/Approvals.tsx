import { useState } from 'react';
import { TAB_TONE, fmt } from '../data/mockData';
import type { TabType } from '../types';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Button } from '../components/shared/Button';
import { Icons } from '../components/shared/Icons';

const APPROVALS = [
  { id: 1, type: '월별 근무기록', unit: '공익활동형'   as TabType, submitter: '이사복', submitDate: '2026.05.18', count: '12건', amount: 4800000, status: '대기중', priority: 'high',   approvedBy: '',   approvedDate: '', reason: '' },
  { id: 2, type: '지출 등록',     unit: '사회서비스형' as TabType, submitter: '이사복', submitDate: '2026.05.17', count: '3건',  amount: 320000,  status: '대기중', priority: 'normal', approvedBy: '',   approvedDate: '', reason: '' },
  { id: 3, type: '상담 보고서',   unit: '공익활동형'   as TabType, submitter: '김복지', submitDate: '2026.05.17', count: '1건',  amount: 0,       status: '대기중', priority: 'normal', approvedBy: '',   approvedDate: '', reason: '' },
  { id: 4, type: '어르신 등록',   unit: '시장형'       as TabType, submitter: '이사복', submitDate: '2026.05.16', count: '2건',  amount: 0,       status: '대기중', priority: 'normal', approvedBy: '',   approvedDate: '', reason: '' },
  { id: 5, type: '월별 근무기록', unit: '공익활동형'   as TabType, submitter: '김복지', submitDate: '2026.05.10', count: '10건', amount: 1200000, status: '승인',   priority: 'normal', approvedBy: '센터장', approvedDate: '2026.05.11', reason: '' },
  { id: 6, type: '지출 등록',     unit: '공익활동형'   as TabType, submitter: '김복지', submitDate: '2026.05.05', count: '1건',  amount: 45000,   status: '반려',   priority: 'normal', approvedBy: '',   approvedDate: '', reason: '영수증 누락 — 보완 후 재제출' },
];

export function Approvals() {
  const [filter, setFilter] = useState('대기중');

  const counts = {
    '대기중': APPROVALS.filter((a) => a.status === '대기중').length,
    '승인':   APPROVALS.filter((a) => a.status === '승인').length,
    '반려':   APPROVALS.filter((a) => a.status === '반려').length,
  };

  const filtered = APPROVALS.filter((a) => filter === '전체' || a.status === filter);

  return (
    <>
      <div style={{ display: 'flex', gap: 14, marginBottom: 20 }}>
        {[
          { key: '전체',  val: APPROVALS.length,  color: 'var(--ink-900)' },
          { key: '대기중', val: counts['대기중'], color: 'var(--warm)'    },
          { key: '승인',   val: counts['승인'],   color: 'var(--green-700)' },
          { key: '반려',   val: counts['반려'],   color: 'var(--danger)'  },
        ].map((s) => (
          <div key={s.key} onClick={() => setFilter(s.key)} style={{
            flex: 1, padding: '20px 24px', background: '#fff',
            border: `1.5px solid ${filter === s.key ? s.color : 'var(--line)'}`,
            borderRadius: 16, cursor: 'pointer',
            boxShadow: filter === s.key ? 'var(--shadow)' : 'var(--shadow-sm)',
          }}>
            <div style={{ fontSize: 14, color: 'var(--ink-500)', fontWeight: 600 }}>{s.key}</div>
            <div className="num" style={{ fontSize: 32, fontWeight: 800, color: s.color, marginTop: 6 }}>
              {s.val}<span style={{ fontSize: 16, color: 'var(--ink-500)', marginLeft: 4 }}>건</span>
            </div>
          </div>
        ))}
      </div>

      <Card title={`결재 목록 — ${filter}`} padding="0">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
          <thead>
            <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
              {['문서 종류', '사업단', '제출자', '제출일', '건수', '금액', '상태', '결재'].map((h) => (
                <th key={h} style={{ padding: '14px 18px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((a) => (
              <tr key={a.id} style={{ borderTop: '1px solid var(--line-soft)', background: a.priority === 'high' && a.status === '대기중' ? 'var(--cream-50)' : '#fff' }}>
                <td style={{ padding: '16px 18px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    {a.priority === 'high' && a.status === '대기중' && <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--warm)', display: 'inline-block' }}/>}
                    <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink-900)' }}>{a.type}</span>
                  </div>
                </td>
                <td style={{ padding: '16px 18px' }}>
                  <Chip tone={TAB_TONE[a.unit].chip as 'green'|'info'|'warm'} size="sm">{a.unit}</Chip>
                </td>
                <td style={{ padding: '16px 18px', color: 'var(--ink-700)' }}>{a.submitter}</td>
                <td className="num" style={{ padding: '16px 18px', color: 'var(--ink-700)' }}>{a.submitDate}</td>
                <td style={{ padding: '16px 18px', fontWeight: 600 }}>{a.count}</td>
                <td className="num" style={{ padding: '16px 18px', fontWeight: 700, color: a.amount ? 'var(--ink-900)' : 'var(--ink-400)' }}>
                  {a.amount ? fmt(a.amount) + '원' : '—'}
                </td>
                <td style={{ padding: '16px 18px' }}>
                  <Chip tone={a.status === '승인' ? 'green' : a.status === '반려' ? 'danger' : 'warm'} size="sm">{a.status}</Chip>
                  {a.status === '승인' && <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 4 }}>{a.approvedBy} · {a.approvedDate}</div>}
                  {a.status === '반려' && <div style={{ fontSize: 11, color: 'var(--danger)', marginTop: 4, maxWidth: 180 }}>{a.reason}</div>}
                </td>
                <td style={{ padding: '16px 18px' }}>
                  {a.status === '대기중' ? (
                    <div style={{ display: 'flex', gap: 6 }}>
                      <Button variant="primary" size="sm" icon={<Icons.check/>}>승인</Button>
                      <Button variant="ghost" size="sm">반려</Button>
                    </div>
                  ) : (
                    <Button variant="ghost" size="sm">상세 보기</Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}

import { useState } from 'react';
import type { PageType, TabType } from '../types';
import { SENIORS, TAB_TONE } from '../data/mockData';
import { Modal } from '../components/layout/Modal';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Button } from '../components/shared/Button';
import { Icons } from '../components/shared/Icons';

const CONSULTS_DATA = [
  { date: '2026.05.18', time: '10:30', senior: '박영순', unit: '공익활동형'   as TabType, m: '전화', c: '건강 상태 확인 — 무릎 통증 호소. 6월 활동 일부 조정 권고.',     w: '김복지' },
  { date: '2026.05.15', time: '14:00', senior: '김영자', unit: '공익활동형'   as TabType, m: '방문', c: '보건소 환경 정비 작업 적응 양호. 동료 어르신과의 친목도 좋음.', w: '김복지' },
  { date: '2026.05.12', time: '11:20', senior: '박철수', unit: '공익활동형'   as TabType, m: '내방', c: '5월 활동비 수령 확인 및 6월 일정 안내.',                           w: '이사복' },
  { date: '2026.05.10', time: '09:15', senior: '최대호', unit: '사회서비스형' as TabType, m: '전화', c: '어린이집 보육 도우미 업무 만족도 높음. 7월 휴가 일정 협의.',       w: '김복지' },
  { date: '2026.05.07', time: '15:45', senior: '정미숙', unit: '사회서비스형' as TabType, m: '방문', c: '복지관 활동 시간 조정 요청 — 가족 행사로 5/28-30 결근 예정.',     w: '이사복' },
  { date: '2026.05.05', time: '10:00', senior: '이순희', unit: '공익활동형'   as TabType, m: '기타', c: '온라인 안전교육 이수 안내.',                                         w: '김복지' },
];

const STATS = [
  { lb: '이번달 상담',       val: '24건',  color: 'var(--green-700)' },
  { lb: '미상담 어르신',     val: '3명',   color: 'var(--danger)'    },
  { lb: '30일 이상 미상담', val: '1명',   color: 'var(--warm)'      },
  { lb: '평균 상담 주기',    val: '12일',  color: 'var(--info)'      },
];

interface ConsultProps {
  onNavigate: (page: PageType, seniorId?: number) => void;
}

export function Consult({ onNavigate }: ConsultProps) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState('전체');

  const filtered = CONSULTS_DATA.filter((c) => filter === '전체' || c.m === filter);

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
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="secondary" size="sm" icon={<Icons.download/>}>Excel</Button>
          <Button variant="secondary" size="sm" icon={<Icons.download/>}>PDF</Button>
          <Button variant="primary" size="sm" icon={<Icons.plus/>} onClick={() => setOpen(true)}>상담 등록</Button>
        </div>
      </div>

      <div className="g4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 18 }}>
        {STATS.map((s) => (
          <div key={s.lb} style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 18, padding: '16px 18px', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>{s.lb}</div>
            <div className="num" style={{ fontSize: 26, fontWeight: 800, color: s.color, marginTop: 4 }}>{s.val}</div>
          </div>
        ))}
      </div>

      <Card title={`상담 기록 (${filtered.length}건)`} padding="0">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
          <thead>
            <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
              {['상담일시', '어르신', '사업단', '방법', '상담 내용', '담당자', ''].map((h) => (
                <th key={h} style={{ padding: '14px 18px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((c, i) => (
              <tr key={i} style={{ borderTop: '1px solid var(--line-soft)' }}>
                <td style={{ padding: '14px 18px' }}>
                  <div className="num" style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink-900)' }}>{c.date}</div>
                  <div className="num" style={{ fontSize: 13, color: 'var(--ink-500)' }}>{c.time}</div>
                </td>
                <td style={{ padding: '14px 18px' }}>
                  <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--green-700)', cursor: 'pointer' }}
                    onClick={() => {
                      const s = SENIORS.find((x) => x.name === c.senior);
                      if (s) onNavigate('seniors', s.id);
                    }}>
                    {c.senior}
                  </span>
                </td>
                <td style={{ padding: '14px 18px' }}>
                  <Chip tone={TAB_TONE[c.unit].chip as 'green'|'info'|'warm'} size="sm">{c.unit}</Chip>
                </td>
                <td style={{ padding: '14px 18px' }}>
                  <Chip tone="green" size="sm">{c.m}</Chip>
                </td>
                <td style={{ padding: '14px 18px', color: 'var(--ink-700)', maxWidth: 480, lineHeight: 1.5 }}>{c.c}</td>
                <td style={{ padding: '14px 18px', fontSize: 14, color: 'var(--ink-700)' }}>{c.w}</td>
                <td style={{ padding: '14px 18px' }}>
                  <Button variant="ghost" size="sm">수정</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} width={620}>
        <div style={{ padding: '28px 32px', borderBottom: '1px solid var(--line)' }}>
          <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--ink-900)' }}>새 상담 등록</div>
          <div style={{ fontSize: 14, color: 'var(--ink-500)', marginTop: 4 }}>저장 시 document_snapshots에 자동 보관됩니다.</div>
        </div>
        <div style={{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[
            { label: '어르신 선택', el: <select style={inputStyle}><option>김영자</option><option>박철수</option><option>이순희</option></select> },
            { label: '상담일시',    el: <input type="datetime-local" defaultValue="2026-05-19T10:30" style={inputStyle}/> },
            { label: '상담 방법',   el: <div style={{ display: 'flex', gap: 8 }}>{['전화','방문','내방','기타'].map(m => <Chip key={m} tone="neutral">{m}</Chip>)}</div> },
            { label: '기본 근무시간', el: <div style={{ fontSize: 16, color: 'var(--ink-500)' }}>3시간/회 <span style={{ fontSize: 12 }}>(표시 전용)</span></div> },
            { label: '상담 내용',   el: <textarea style={{ ...inputStyle, minHeight: 100 }} rows={4} placeholder="상담 내용을 자세히 기록하세요."/> },
            { label: '메모',        el: <textarea style={{ ...inputStyle, minHeight: 60 }} rows={2} placeholder="기타 메모 (선택)"/> },
          ].map((r) => (
            <div key={r.label}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-700)', marginBottom: 6 }}>{r.label}</div>
              {r.el}
            </div>
          ))}
          <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>담당자: <strong>김복지 사회복지사</strong> (자동)</div>
        </div>
        <div style={{ padding: '20px 32px', borderTop: '1px solid var(--line)', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <Button variant="ghost" size="md" onClick={() => setOpen(false)}>취소</Button>
          <Button variant="primary" size="md" icon={<Icons.check/>}>저장</Button>
        </div>
      </Modal>
    </>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '12px 14px', border: '1.5px solid var(--line)',
  borderRadius: 10, fontSize: 15, outline: 'none', background: '#fff', color: 'var(--ink-900)',
  display: 'block',
};

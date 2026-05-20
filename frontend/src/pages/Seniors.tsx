import { useState } from 'react';
import type { PageType, TabType } from '../types';
import { SENIORS, TAB_TONE, fmt } from '../data/mockData';
import { UnitTabBar } from '../components/layout/UnitTabBar';
import { BudgetStrip } from '../components/layout/BudgetStrip';
import { Card } from '../components/layout/Card';
import { Modal } from '../components/layout/Modal';
import { Chip } from '../components/shared/Chip';
import { Button } from '../components/shared/Button';
import { Progress } from '../components/shared/Progress';
import { Icons } from '../components/shared/Icons';

interface SeniorsProps {
  tab: TabType;
  setTab: (t: TabType) => void;
  selectedSenior: number | null;
  setSelectedSenior: (id: number | null) => void;
  onNavigatePage: (page: PageType) => void;
  onFocusSenior: (id: number) => void;
}

export function Seniors({ tab, setTab, selectedSenior, setSelectedSenior, onNavigatePage, onFocusSenior }: SeniorsProps) {
  const [q, setQ] = useState('');
  const [statusFilter, setStatusFilter] = useState('전체');

  const filtered = SENIORS
    .filter((s) => s.unit === tab)
    .filter((s) => !q || s.name.includes(q) || s.wp.includes(q))
    .filter((s) => statusFilter === '전체' || s.status === statusFilter);

  const detail = selectedSenior ? SENIORS.find((s) => s.id === selectedSenior) : null;

  const CONSULTS = detail ? [
    { date: '2026.04.15', m: '전화', c: '건강 상태 확인, 이상 없음', w: detail.sw },
    { date: '2026.03.20', m: '방문', c: '근무 적응 상황 확인',       w: detail.sw },
    { date: '2026.02.11', m: '내방', c: '2월 활동비 수령 확인',      w: detail.sw },
  ] : [];

  return (
    <>
      <UnitTabBar tab={tab} onChange={setTab} right={
        <>
          <Button variant="secondary" size="sm" icon={<Icons.download/>}>Excel</Button>
          <Button variant="primary" size="sm" icon={<Icons.plus/>}>어르신 등록</Button>
        </>
      }/>

      <BudgetStrip tab={tab}/>

      {/* search row */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
        <div style={{
          flex: 1, maxWidth: 360, display: 'flex', alignItems: 'center', gap: 10,
          padding: '12px 16px', background: '#fff', border: '1.5px solid var(--line)', borderRadius: 12,
        }}>
          <Icons.search/>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="이름·근무장소 검색…"
            style={{ flex: 1, border: 'none', outline: 'none', fontSize: 15, background: 'transparent' }}/>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {['전체', '정상', '임박', '미상담'].map((s) => (
            <div key={s} onClick={() => setStatusFilter(s)} style={{
              padding: '10px 14px', borderRadius: 999, fontSize: 14, fontWeight: 600, cursor: 'pointer',
              background: statusFilter === s ? 'var(--green-700)' : '#fff',
              color:      statusFilter === s ? '#fff' : 'var(--ink-700)',
              border:     `1.5px solid ${statusFilter === s ? 'var(--green-700)' : 'var(--line)'}`,
            }}>{s}</div>
          ))}
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 14, color: 'var(--ink-500)' }}>
          총 <strong className="num" style={{ color: 'var(--ink-900)', fontSize: 16 }}>{filtered.length}</strong>명
        </div>
      </div>

      <Card padding="0">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
          <thead>
            <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
              {['이름', '생년월일', '근무장소', '총 근무시간', '남은 시간', '지급 금액', '상담', '상태', ''].map((h) => (
                <th key={h} style={{ padding: '14px 20px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((s) => (
              <tr key={s.id} onClick={() => setSelectedSenior(s.id)} style={{
                borderTop: '1px solid var(--line-soft)', cursor: 'pointer',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--cream-50)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = '')}
              >
                <td style={{ padding: '16px 20px', fontSize: 17, fontWeight: 700, color: 'var(--green-700)' }}>{s.name}</td>
                <td style={{ padding: '16px 20px', color: 'var(--ink-700)' }}>{s.birth}</td>
                <td style={{ padding: '16px 20px', color: 'var(--ink-700)' }}>{s.wp}</td>
                <td style={{ padding: '16px 20px', minWidth: 180 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ flex: 1 }}>
                      <Progress value={Math.min(100, (s.totalH / 330) * 100)} color="var(--green-600)" height={7}/>
                    </div>
                    <span className="num" style={{ fontSize: 13, color: 'var(--ink-700)', fontWeight: 600 }}>{s.totalH}h</span>
                  </div>
                </td>
                <td className="num" style={{ padding: '16px 20px', color: s.remainH < 30 ? 'var(--danger)' : 'var(--ink-700)', fontWeight: s.remainH < 30 ? 700 : 600 }}>{s.remainH}h</td>
                <td className="num" style={{ padding: '16px 20px', color: 'var(--ink-700)', fontWeight: 600 }}>{fmt(s.paid)}원</td>
                <td style={{ padding: '16px 20px' }}>
                  <Chip tone={s.consults === 0 ? 'danger' : 'neutral'} size="sm">{s.consults}건</Chip>
                </td>
                <td style={{ padding: '16px 20px' }}>
                  <Chip tone={s.status === '정상' ? 'green' : s.status === '임박' ? 'danger' : 'warm'} size="sm">{s.status}</Chip>
                </td>
                <td style={{ padding: '16px 20px' }}>
                  <Button variant="ghost" size="sm">상세 →</Button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan={9} style={{ padding: 48, textAlign: 'center', color: 'var(--ink-500)' }}>검색 결과가 없습니다.</td></tr>
            )}
          </tbody>
        </table>
      </Card>

      {/* Detail Modal */}
      {detail && (
        <Modal open={true} onClose={() => setSelectedSenior(null)} width={960}>
          {/* head */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '24px 32px', borderBottom: '1px solid var(--line)', background: '#fff' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
              <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'var(--green-100)', color: 'var(--green-700)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28, fontWeight: 800 }}>
                {detail.name.charAt(0)}
              </div>
              <div>
                <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--ink-900)' }}>
                  {detail.name} <span style={{ fontSize: 16, color: 'var(--ink-500)', fontWeight: 500 }}>· 어르신 상세</span>
                </div>
                <div style={{ fontSize: 14, color: 'var(--ink-500)', marginTop: 4, display: 'flex', gap: 12 }}>
                  <span>{detail.birth} 생</span>
                  <span style={{ color: 'var(--ink-300)' }}>·</span>
                  <span>{detail.phone}</span>
                  <span style={{ color: 'var(--ink-300)' }}>·</span>
                  <Chip tone={TAB_TONE[detail.unit].chip as 'green'|'info'|'warm'} size="sm">{detail.unit}</Chip>
                  <Chip tone={detail.status === '정상' ? 'green' : detail.status === '임박' ? 'danger' : 'warm'} size="sm">{detail.status}</Chip>
                </div>
              </div>
            </div>
            <button onClick={() => setSelectedSenior(null)} style={{ width: 44, height: 44, borderRadius: 12, border: '1.5px solid var(--line)', background: '#fff', fontSize: 22, cursor: 'pointer', color: 'var(--ink-700)' }}>×</button>
          </div>

          {/* body */}
          <div style={{ padding: '24px 32px', display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24 }}>
            {/* left */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 16, padding: '20px 22px' }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-900)', marginBottom: 14 }}>기본 정보</div>
                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-500)', marginBottom: 6 }}>근무장소 <span style={{ color: 'var(--green-700)' }}>(수정 가능)</span></div>
                  <input defaultValue={detail.wp} style={{ width: '100%', padding: '10px 12px', border: '1.5px solid var(--line)', borderRadius: 10, fontSize: 15, outline: 'none', background: '#fff' }}/>
                </div>
                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-500)', marginBottom: 6 }}>기본 근무시간 <span style={{ color: 'var(--green-700)' }}>(수정 가능)</span></div>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <input defaultValue="3" style={{ width: 80, padding: '10px 12px', border: '1.5px solid var(--line)', borderRadius: 10, fontSize: 15, textAlign: 'center', outline: 'none' }}/>
                    <span style={{ fontSize: 14, color: 'var(--ink-700)' }}>시간/회</span>
                    <Chip tone="green" size="sm">기본 3h</Chip>
                  </div>
                </div>
                {[['담당 사복사', detail.sw], ['사업단', detail.unit]].map(([l, v]) => (
                  <div key={l} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderTop: '1px solid var(--line-soft)', fontSize: 14 }}>
                    <span style={{ color: 'var(--ink-500)' }}>{l}</span>
                    <span style={{ fontWeight: 600, color: 'var(--ink-900)' }}>{v}</span>
                  </div>
                ))}
                <Button variant="primary" size="sm" full>저장</Button>
              </div>

              <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 16, padding: '20px 22px' }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-900)', marginBottom: 14 }}>📊 근무 현황</div>
                {[
                  ['총 근무시간',  `${detail.totalH}시간`,  'var(--green-700)'],
                  ['남은 시간',    `${detail.remainH}시간`, detail.remainH < 30 ? 'var(--danger)' : 'var(--ink-900)'],
                  ['지급 금액',    `${fmt(detail.paid)}원`, 'var(--ink-900)'],
                  ['남은 금액',    '540,000원',             'var(--green-700)'],
                ].map(([l, v, c]) => (
                  <div key={l as string} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line-soft)', fontSize: 14 }}>
                    <span style={{ color: 'var(--ink-500)' }}>{l}</span>
                    <span className="num" style={{ fontWeight: 700, color: c as string }}>{v}</span>
                  </div>
                ))}
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 6, display: 'flex', justifyContent: 'space-between' }}>
                    <span>연간 소진율</span>
                    <span className="num" style={{ fontWeight: 700 }}>{detail.totalH}/330h</span>
                  </div>
                  <Progress value={Math.min(100, (detail.totalH / 330) * 100)} color="var(--green-600)" height={10}/>
                </div>
                <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <Button variant="primary" size="md" full icon={<Icons.briefcase/>}
                    onClick={() => { setSelectedSenior(null); onFocusSenior(detail.id); onNavigatePage('work'); }}>
                    이번달 근무 등록
                  </Button>
                  <Button variant="secondary" size="md" full icon={<Icons.download/>}>개인 근무일지 생성</Button>
                </div>
              </div>
            </div>

            {/* right */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 16, padding: '20px 22px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink-900)' }}>📝 최근 상담 이력</div>
                  <Button variant="primary" size="sm" icon={<Icons.plus/>}
                    onClick={() => { setSelectedSenior(null); onNavigatePage('consult'); }}>
                    상담 등록
                  </Button>
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                  <thead>
                    <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
                      {['상담일자', '방법', '내용', '담당자'].map((h) => (
                        <th key={h} style={{ padding: '10px 14px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 12 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {CONSULTS.map((c, i) => (
                      <tr key={i} style={{ borderTop: '1px solid var(--line-soft)' }}>
                        <td style={{ padding: '12px 14px', fontWeight: 600 }}>{c.date}</td>
                        <td style={{ padding: '12px 14px' }}><Chip tone="green" size="sm">{c.m}</Chip></td>
                        <td style={{ padding: '12px 14px', color: 'var(--ink-700)' }}>{c.c}</td>
                        <td style={{ padding: '12px 14px' }}>{c.w}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 16, padding: '20px 22px', flex: 1 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink-900)', marginBottom: 12 }}>메모</div>
                <textarea defaultValue={detail.note} placeholder="어르신에 대한 메모를 입력하세요." style={{ width: '100%', minHeight: 120, padding: '12px 14px', border: '1.5px solid var(--line)', borderRadius: 10, fontSize: 15, outline: 'none', resize: 'vertical', lineHeight: 1.6 }}/>
                <div style={{ marginTop: 12, textAlign: 'right' }}>
                  <Button variant="primary" size="sm">메모 저장</Button>
                </div>
              </div>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}

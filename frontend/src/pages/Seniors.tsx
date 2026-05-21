import { useState } from 'react';
import type { PageType, TabType } from '../types';
import { useAppStore } from '../stores/appStore';
import { useBusinessUnits } from '../hooks/useBusinessUnits';
import { useSeniors, type ApiSenior } from '../hooks/useSeniors';
import { useConsultationLogs } from '../hooks/useConsultationLogs';
import { TAB_TONE } from '../data/mockData';
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

function birthDisplay(d: string) {
  return d ? d.replace(/-/g, '.') : '—';
}

export function Seniors({ tab, setTab, selectedSenior: _selectedSenior, setSelectedSenior, onNavigatePage, onFocusSenior }: SeniorsProps) {
  const year = useAppStore((s) => s.year);
  const { byTab } = useBusinessUnits(year);
  const bu = byTab(tab);
  const { seniors, loading } = useSeniors(bu?.id ?? null);
  const [q, setQ] = useState('');
  const [selectedUuid, setSelectedUuid] = useState<string | null>(null);

  const filtered = seniors.filter((s) =>
    !q || s.name.includes(q) || s.workplace.includes(q)
  );

  const detail = selectedUuid ? seniors.find((s) => s.id === selectedUuid) ?? null : null;

  const handleSelectSenior = (s: ApiSenior) => {
    setSelectedUuid(s.id);
    setSelectedSenior(s.id.charCodeAt(0));
  };

  return (
    <>
      <UnitTabBar tab={tab} onChange={setTab} right={
        <>
          <Button variant="secondary" size="sm" icon={<Icons.download/>}>Excel</Button>
          <Button variant="primary" size="sm" icon={<Icons.plus/>}>어르신 등록</Button>
        </>
      }/>

      <BudgetStrip tab={tab}/>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
        <div style={{
          flex: 1, maxWidth: 360, display: 'flex', alignItems: 'center', gap: 10,
          padding: '12px 16px', background: '#fff', border: '1.5px solid var(--line)', borderRadius: 12,
        }}>
          <Icons.search/>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="이름·근무장소 검색…"
            style={{ flex: 1, border: 'none', outline: 'none', fontSize: 15, background: 'transparent' }}/>
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 14, color: 'var(--ink-500)' }}>
          총 <strong className="num" style={{ color: 'var(--ink-900)', fontSize: 16 }}>{filtered.length}</strong>명
        </div>
      </div>

      <Card padding="0">
        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: 'var(--ink-400)' }}>로딩 중…</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
            <thead>
              <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
                {['이름', '생년월일', '근무장소', '배정시간', '기본시간/회', ''].map((h) => (
                  <th key={h} style={{ padding: '14px 20px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id} onClick={() => handleSelectSenior(s)} style={{ borderTop: '1px solid var(--line-soft)', cursor: 'pointer' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--cream-50)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = '')}>
                  <td style={{ padding: '16px 20px', fontSize: 17, fontWeight: 700, color: 'var(--green-700)' }}>{s.name}</td>
                  <td style={{ padding: '16px 20px', color: 'var(--ink-700)' }}>{birthDisplay(s.birth_date)}</td>
                  <td style={{ padding: '16px 20px', color: 'var(--ink-700)' }}>{s.workplace || '—'}</td>
                  <td style={{ padding: '16px 20px', minWidth: 160 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ flex: 1 }}>
                        <Progress value={0} color="var(--green-600)" height={7}/>
                      </div>
                      <span className="num" style={{ fontSize: 13, color: 'var(--ink-700)', fontWeight: 600 }}>{s.allocated_hours}h</span>
                    </div>
                  </td>
                  <td className="num" style={{ padding: '16px 20px', color: 'var(--ink-700)', fontWeight: 600 }}>{s.default_session_hours}h</td>
                  <td style={{ padding: '16px 20px' }}>
                    <Button variant="ghost" size="sm">상세 →</Button>
                  </td>
                </tr>
              ))}
              {!loading && filtered.length === 0 && (
                <tr><td colSpan={6} style={{ padding: 48, textAlign: 'center', color: 'var(--ink-400)' }}>
                  {bu ? '등록된 어르신이 없습니다.' : '이 유형의 사업단이 등록되지 않았습니다.'}
                </td></tr>
              )}
            </tbody>
          </table>
        )}
      </Card>

      {detail && (
        <SeniorDetailModal
          senior={detail}
          tab={tab}
          onClose={() => setSelectedUuid(null)}
          onNavigatePage={onNavigatePage}
          onFocusSenior={onFocusSenior}
        />
      )}
    </>
  );
}

function SeniorDetailModal({ senior, tab, onClose, onNavigatePage, onFocusSenior }: {
  senior: ApiSenior;
  tab: TabType;
  onClose: () => void;
  onNavigatePage: (p: PageType) => void;
  onFocusSenior: (id: number) => void;
}) {
  const { logs } = useConsultationLogs(senior.id);
  const recentLogs = logs.slice(0, 5);

  const METHOD_LABEL: Record<string, string> = {
    phone: '전화', visit: '방문', in_person: '내방', other: '기타',
  };

  return (
    <Modal open onClose={onClose} width={960}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '24px 32px', borderBottom: '1px solid var(--line)', background: '#fff' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'var(--green-100)', color: 'var(--green-700)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28, fontWeight: 800 }}>
            {senior.name.charAt(0)}
          </div>
          <div>
            <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--ink-900)' }}>
              {senior.name} <span style={{ fontSize: 16, color: 'var(--ink-500)', fontWeight: 500 }}>· 어르신 상세</span>
            </div>
            <div style={{ fontSize: 14, color: 'var(--ink-500)', marginTop: 4, display: 'flex', gap: 12 }}>
              <span>{birthDisplay(senior.birth_date)} 생</span>
              <span style={{ color: 'var(--ink-300)' }}>·</span>
              <Chip tone={TAB_TONE[tab].chip as 'green' | 'info' | 'warm'} size="sm">{tab}</Chip>
            </div>
          </div>
        </div>
        <button onClick={onClose} style={{ width: 44, height: 44, borderRadius: 12, border: '1.5px solid var(--line)', background: '#fff', fontSize: 22, cursor: 'pointer', color: 'var(--ink-700)' }}>×</button>
      </div>

      <div style={{ padding: '24px 32px', display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 16, padding: '20px 22px' }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-900)', marginBottom: 14 }}>기본 정보</div>
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-500)', marginBottom: 6 }}>근무장소</div>
              <input defaultValue={senior.workplace} style={{ width: '100%', padding: '10px 12px', border: '1.5px solid var(--line)', borderRadius: 10, fontSize: 15, outline: 'none', background: '#fff', boxSizing: 'border-box' }}/>
            </div>
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-500)', marginBottom: 6 }}>기본 근무시간</div>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <span className="num" style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink-900)' }}>{senior.default_session_hours}시간/회</span>
                <Chip tone="green" size="sm">기본 {senior.default_session_hours}h</Chip>
              </div>
            </div>
            <Button variant="primary" size="sm" full>저장</Button>
          </div>

          <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 16, padding: '20px 22px' }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-900)', marginBottom: 14 }}>📊 근무 현황</div>
            {[
              ['배정 시간', `${senior.allocated_hours}시간`, 'var(--green-700)'],
              ['시급', `${senior.hourly_wage.toLocaleString()}원`, 'var(--ink-900)'],
            ].map(([l, v, c]) => (
              <div key={l as string} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line-soft)', fontSize: 14 }}>
                <span style={{ color: 'var(--ink-500)' }}>{l}</span>
                <span className="num" style={{ fontWeight: 700, color: c as string }}>{v}</span>
              </div>
            ))}
            <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <Button variant="primary" size="md" full icon={<Icons.briefcase/>}
                onClick={() => { onClose(); onFocusSenior(senior.id.charCodeAt(0)); onNavigatePage('work'); }}>
                이번달 근무 등록
              </Button>
              <Button variant="secondary" size="md" full icon={<Icons.download/>}>개인 근무일지 생성</Button>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 16, padding: '20px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink-900)' }}>📝 최근 상담 이력 ({logs.length}건)</div>
              <Button variant="primary" size="sm" icon={<Icons.plus/>}
                onClick={() => { onClose(); onNavigatePage('consult'); }}>
                상담 등록
              </Button>
            </div>
            {recentLogs.length === 0 ? (
              <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--ink-400)', fontSize: 14 }}>상담 기록이 없습니다.</div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                <thead>
                  <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
                    {['상담일자', '방법', '내용'].map((h) => (
                      <th key={h} style={{ padding: '10px 14px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 12 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recentLogs.map((c) => (
                    <tr key={c.id} style={{ borderTop: '1px solid var(--line-soft)' }}>
                      <td style={{ padding: '12px 14px', fontWeight: 600 }}>{c.consultation_date.slice(0, 10).replace(/-/g, '.')}</td>
                      <td style={{ padding: '12px 14px' }}><Chip tone="green" size="sm">{METHOD_LABEL[c.method] ?? c.method}</Chip></td>
                      <td style={{ padding: '12px 14px', color: 'var(--ink-700)', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.content}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 16, padding: '20px 22px', flex: 1 }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink-900)', marginBottom: 12 }}>메모</div>
            <textarea defaultValue={senior.notes ?? ''} placeholder="어르신에 대한 메모를 입력하세요." style={{ width: '100%', minHeight: 120, padding: '12px 14px', border: '1.5px solid var(--line)', borderRadius: 10, fontSize: 15, outline: 'none', resize: 'vertical', lineHeight: 1.6, boxSizing: 'border-box' }}/>
            <div style={{ marginTop: 12, textAlign: 'right' }}>
              <Button variant="primary" size="sm">메모 저장</Button>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}


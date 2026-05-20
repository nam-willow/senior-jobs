import type { PageType, TabType } from '../types';
import { BUDGET, ALERTS, ORGS, MONTHLY, TABS, TAB_TONE, fmt, won } from '../data/mockData';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Donut } from '../components/shared/Donut';
import { Progress } from '../components/shared/Progress';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';

interface DashboardProps {
  onNavigate: (page: PageType, tab?: TabType) => void;
}

export function Dashboard({ onNavigate }: DashboardProps) {
  const totalSeniors = Object.values(BUDGET).reduce((s, b) => s + b.count, 0);

  return (
    <>
      {/* ─── KPI row ─────────────────────────────── */}
      <div className="g4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 28 }}>
        {[
          { lb: '총 참여 어르신', val: `${totalSeniors}명`, sub: '3개 사업단 합계', color: 'var(--green-700)', bg: 'var(--green-50)' },
          { lb: '이번달 급여 예정', val: won(4800000), sub: '공익 + 사회 + 시장', color: 'var(--ink-900)', bg: '#fff' },
          { lb: '결재 대기', val: '12건', sub: '월별 근무기록', color: 'var(--warm)', bg: 'var(--warm-soft)' },
          { lb: '미상담 어르신', val: '2명', sub: '30일 이상 무상담', color: 'var(--danger)', bg: '#FBE3E3' },
        ].map((s) => (
          <div key={s.lb} style={{
            background: s.bg, border: '1px solid var(--line)', borderRadius: 18,
            padding: '22px 24px', boxShadow: 'var(--shadow-sm)',
          }}>
            <div style={{ fontSize: 13, color: 'var(--ink-500)', marginBottom: 8 }}>{s.lb}</div>
            <div className="num" style={{ fontSize: 26, fontWeight: 800, color: s.color }}>{s.val}</div>
            <div style={{ fontSize: 12, color: 'var(--ink-400)', marginTop: 6 }}>{s.sub}</div>
          </div>
        ))}
      </div>

      {/* ─── Budget donut cards ───────────────────── */}
      <div className="g3" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 18, marginBottom: 28 }}>
        {TABS.map((tab) => {
          const b = BUDGET[tab];
          const tone = TAB_TONE[tab];
          return (
            <div key={tab} onClick={() => onNavigate('budget', tab)} style={{
              background: '#fff', border: '1px solid var(--line)', borderRadius: 20,
              padding: '24px', boxShadow: 'var(--shadow-sm)', cursor: 'pointer',
              transition: 'box-shadow .15s',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--ink-900)' }}>{tab}</div>
                  <div style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 2 }}>{b.count}명 참여</div>
                </div>
                <Chip tone={b.pct > 90 ? 'danger' : b.pct > 70 ? 'warm' : 'green'} size="sm">{b.pct}% 집행</Chip>
              </div>
              <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
                <Donut value={b.pct} color={tone.color} size={100} label={`${b.pct}%`}/>
                <div style={{ flex: 1 }}>
                  {b.lines.map((line) => (
                    <div key={line.l} style={{ marginBottom: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>
                        <span>{line.l}</span>
                        <span className="num">{line.pct}%</span>
                      </div>
                      <Progress value={line.pct} color={line.total === 0 ? 'var(--line)' : tone.color} height={6}/>
                    </div>
                  ))}
                  <div className="num" style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 6 }}>
                    잔액 <strong style={{ color: tone.color }}>{won(b.remain)}</strong>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20, marginBottom: 28 }}>
        {/* Monthly hours bar chart */}
        <Card title="월별 근무시간 추이 (시간)">
          <div style={{ height: 240, marginTop: 8 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={MONTHLY} barSize={16} barGap={4}>
                <XAxis dataKey="m" tick={{ fontSize: 12, fill: 'var(--ink-500)' }} axisLine={false} tickLine={false}/>
                <YAxis tick={{ fontSize: 12, fill: 'var(--ink-500)' }} axisLine={false} tickLine={false}/>
                <Tooltip formatter={(v) => [`${v}h`]} contentStyle={{ borderRadius: 10, border: '1px solid var(--line)' }}/>
                <Legend wrapperStyle={{ fontSize: 12 }}/>
                <Bar dataKey="pub" name="공익활동형"   fill="var(--green-600)" radius={[4,4,0,0]}/>
                <Bar dataKey="svc" name="사회서비스형" fill="var(--info)"      radius={[4,4,0,0]}/>
                <Bar dataKey="mkt" name="시장형"       fill="var(--warm)"      radius={[4,4,0,0]}/>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Alerts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontSize: 17, fontWeight: 800, color: 'var(--ink-900)' }}>🔔 주요 알림</span>
            <span onClick={() => onNavigate('alerts')} style={{ fontSize: 13, color: 'var(--green-700)', cursor: 'pointer', fontWeight: 600 }}>전체 보기 →</span>
          </div>
          {ALERTS.map((a) => {
            const toneMap = { danger: 'var(--danger)', warm: 'var(--warm)', gold: 'var(--gold)', info: 'var(--info)' } as const;
            const dot = toneMap[a.tone];
            return (
              <div key={a.id} onClick={() => a.goto && onNavigate(a.goto, a.tab)} style={{
                background: '#fff', border: '1px solid var(--line)', borderRadius: 14,
                padding: '14px 16px', cursor: 'pointer',
              }}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: dot, marginTop: 6, flexShrink: 0 }}/>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-900)' }}>{a.title}</div>
                    <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 2 }}>{a.meta} · {a.t}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Org table */}
      <Card title="기관 현황">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: 'left' }}>
              {['기관명', '지역', '유형', '참여인원', '누적시간', '집행률', '상태'].map((h) => (
                <th key={h} style={{ padding: '10px 16px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 12, borderBottom: '1px solid var(--line-soft)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ORGS.map((o) => (
              <tr key={o.name} style={{ borderTop: '1px solid var(--line-soft)' }}>
                <td style={{ padding: '12px 16px', fontWeight: 700, color: 'var(--ink-900)' }}>{o.name}</td>
                <td style={{ padding: '12px 16px', color: 'var(--ink-500)' }}>{o.area}</td>
                <td style={{ padding: '12px 16px' }}>
                  <Chip tone={TAB_TONE[o.type as TabType].chip as 'green'|'info'|'warm'} size="sm">{o.type}</Chip>
                </td>
                <td className="num" style={{ padding: '12px 16px', color: 'var(--ink-700)' }}>{o.n}명</td>
                <td className="num" style={{ padding: '12px 16px', color: 'var(--ink-700)' }}>{fmt(o.hrs)}h</td>
                <td style={{ padding: '12px 16px', minWidth: 140 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1 }}>
                      <Progress value={o.exec} color={o.exec > 90 ? 'var(--danger)' : 'var(--green-600)'} height={6}/>
                    </div>
                    <span className="num" style={{ fontSize: 12, fontWeight: 700, color: o.exec > 90 ? 'var(--danger)' : 'var(--ink-700)' }}>{o.exec}%</span>
                  </div>
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <Chip tone={o.state === '정상' ? 'green' : 'warn' as 'warm'} size="sm">{o.state}</Chip>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}

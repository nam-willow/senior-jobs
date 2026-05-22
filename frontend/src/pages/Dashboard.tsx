import { useAppStore } from '../stores/appStore';
import { useDashboardSummary } from '../hooks/useDashboardSummary';
import { useAlerts } from '../hooks/useAlerts';
import { useMonthlyHours } from '../hooks/useMonthlyHours';
import type { PageType, TabType } from '../types';
import { TABS, TAB_TONE, fmt, won } from '../data/mockData';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Donut } from '../components/shared/Donut';
import { Progress } from '../components/shared/Progress';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';

const TYPE_KEY: Record<TabType, string> = {
  '공익활동형': 'public_benefit',
  '사회서비스형': 'social_service',
  '시장형': 'market',
};

const TONE_MAP: Record<string, string> = {
  danger: 'var(--danger)',
  warm: 'var(--warm)',
  gold: 'var(--gold)',
  info: 'var(--info)',
};

interface DashboardProps {
  onNavigate: (page: PageType, tab?: TabType) => void;
}

export function Dashboard({ onNavigate }: DashboardProps) {
  const year = useAppStore((s) => s.year);
  const { data: summary, loading: summaryLoading } = useDashboardSummary(year);
  const { alerts, loading: alertsLoading } = useAlerts(year);
  const { monthly, loading: monthlyLoading } = useMonthlyHours(year);

  const totalSeniors = summary
    ? summary.summary.reduce((s, b) => s + b.senior_count, 0)
    : 0;

  const pendingAlert = alerts.find((a) => a.goto === 'approvals');
  const pendingCount = pendingAlert
    ? parseInt(pendingAlert.title.match(/\d+/)?.[0] ?? '0', 10)
    : 0;
  const noConsultAlerts = alerts.filter((a) => a.id.startsWith('consult_'));

  return (
    <>
      {/* ─── KPI row ─────────────────────────────── */}
      <div className="g4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 28 }}>
        {[
          { lb: '총 참여 어르신', val: `${totalSeniors}명`, sub: '3개 사업단 합계', color: 'var(--green-700)', bg: 'var(--green-50)' },
          { lb: '결재 대기', val: `${pendingCount}건`, sub: '월별 근무기록', color: 'var(--warm)', bg: 'var(--warm-soft)' },
          { lb: '미상담 어르신', val: `${noConsultAlerts.length}명`, sub: '30일 이상 무상담', color: 'var(--danger)', bg: '#FBE3E3' },
        ].map((s) => (
          <div key={s.lb} style={{
            background: s.bg, border: '1px solid var(--line)', borderRadius: 18,
            padding: '22px 24px', boxShadow: 'var(--shadow-sm)',
          }}>
            <div style={{ fontSize: 13, color: 'var(--ink-500)', marginBottom: 8 }}>{s.lb}</div>
            <div className="num" style={{ fontSize: 26, fontWeight: 800, color: s.color }}>{s.val}</div>
          </div>
        ))}
        <div style={{
          background: '#fff', border: '1px solid var(--line)', borderRadius: 18,
          padding: '22px 24px', boxShadow: 'var(--shadow-sm)',
        }}>
          <div style={{ fontSize: 13, color: 'var(--ink-500)', marginBottom: 8 }}>총 사업비 집행</div>
          <div className="num" style={{ fontSize: 26, fontWeight: 800, color: 'var(--ink-900)' }}>
            {summary ? `${Math.round(summary.summary.reduce((s, b) => s + b.achievement_rate, 0) / (summary.summary.length || 1))}%` : '—'}
          </div>
          <div style={{ fontSize: 12, color: 'var(--ink-400)', marginTop: 6 }}>평균 집행률</div>
        </div>
      </div>

      {/* ─── Budget donut cards ───────────────────── */}
      <div className="g3" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 18, marginBottom: 28 }}>
        {summaryLoading && (
          <div style={{ gridColumn: '1/-1', textAlign: 'center', color: 'var(--ink-400)', padding: 40 }}>로딩 중...</div>
        )}
        {!summaryLoading && TABS.map((tab) => {
          const apiData = summary?.summary.find((s) => s.type === TYPE_KEY[tab]);
          const pct = apiData ? Math.min(Math.round(apiData.achievement_rate), 100) : 0;
          const tone = TAB_TONE[tab];
          const lines = apiData ? [
            { l: '어르신 임금', pct: Math.round(apiData.breakdown.wage.rate), total: apiData.breakdown.wage.budget },
            { l: '담당자 임금', pct: Math.round(apiData.breakdown.manager_wage.rate), total: apiData.breakdown.manager_wage.budget },
            { l: '사업진행비',  pct: Math.round(apiData.breakdown.operation.rate), total: apiData.breakdown.operation.budget },
          ] : [];
          return (
            <div key={tab} onClick={() => onNavigate('budget', tab)} style={{
              background: '#fff', border: '1px solid var(--line)', borderRadius: 20,
              padding: '24px', boxShadow: 'var(--shadow-sm)', cursor: 'pointer',
              transition: 'box-shadow .15s',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--ink-900)' }}>{tab}</div>
                  <div style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 2 }}>{apiData?.senior_count ?? 0}명 참여</div>
                </div>
                <Chip tone={pct > 90 ? 'danger' : pct > 70 ? 'warm' : 'green'} size="sm">{pct}% 집행</Chip>
              </div>
              <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
                <Donut value={pct} color={tone.color} size={100} label={`${pct}%`}/>
                <div style={{ flex: 1 }}>
                  {lines.map((line) => (
                    <div key={line.l} style={{ marginBottom: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--ink-500)', marginBottom: 4 }}>
                        <span>{line.l}</span>
                        <span className="num">{line.pct}%</span>
                      </div>
                      <Progress value={line.pct} color={line.total === 0 ? 'var(--line)' : tone.color} height={6}/>
                    </div>
                  ))}
                  <div className="num" style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 6 }}>
                    잔액 <strong style={{ color: tone.color }}>{won(apiData?.remaining ?? 0)}</strong>
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
            {monthlyLoading ? (
              <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-400)' }}>로딩 중...</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthly} barSize={16} barGap={4}>
                  <XAxis dataKey="m" tick={{ fontSize: 12, fill: 'var(--ink-500)' }} axisLine={false} tickLine={false}/>
                  <YAxis tick={{ fontSize: 12, fill: 'var(--ink-500)' }} axisLine={false} tickLine={false}/>
                  <Tooltip formatter={(v) => [`${v}h`]} contentStyle={{ borderRadius: 10, border: '1px solid var(--line)' }}/>
                  <Legend wrapperStyle={{ fontSize: 12 }}/>
                  <Bar dataKey="pub" name="공익활동형"   fill="var(--green-600)" radius={[4,4,0,0]}/>
                  <Bar dataKey="svc" name="사회서비스형" fill="var(--info)"      radius={[4,4,0,0]}/>
                  <Bar dataKey="mkt" name="시장형"       fill="var(--warm)"      radius={[4,4,0,0]}/>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        {/* Alerts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontSize: 17, fontWeight: 800, color: 'var(--ink-900)' }}>🔔 주요 알림</span>
            <span onClick={() => onNavigate('alerts')} style={{ fontSize: 13, color: 'var(--green-700)', cursor: 'pointer', fontWeight: 600 }}>전체 보기 →</span>
          </div>
          {alertsLoading && <div style={{ color: 'var(--ink-400)', fontSize: 14, padding: '12px 0' }}>로딩 중...</div>}
          {!alertsLoading && alerts.length === 0 && (
            <div style={{ color: 'var(--ink-400)', fontSize: 14, padding: '12px 0' }}>알림이 없습니다.</div>
          )}
          {!alertsLoading && alerts.slice(0, 5).map((a) => {
            const dot = TONE_MAP[a.tone] ?? 'var(--ink-400)';
            return (
              <div key={a.id} onClick={() => a.goto && onNavigate(a.goto as PageType, a.tab)} style={{
                background: '#fff', border: '1px solid var(--line)', borderRadius: 14,
                padding: '14px 16px', cursor: a.goto ? 'pointer' : 'default',
              }}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: dot, marginTop: 6, flexShrink: 0 }}/>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-900)' }}>{a.title}</div>
                    <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 2 }}>{a.meta}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Summary table */}
      <Card title="사업단별 현황">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: 'left' }}>
              {['사업단 유형', '참여인원', '총 예산', '지출 누계', '잔액', '집행률'].map((h) => (
                <th key={h} style={{ padding: '10px 16px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 12, borderBottom: '1px solid var(--line-soft)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {summaryLoading ? (
              <tr><td colSpan={6} style={{ padding: '24px 16px', color: 'var(--ink-400)', textAlign: 'center' }}>로딩 중...</td></tr>
            ) : summary?.summary.map((s) => {
              const tab = TABS.find((t) => TYPE_KEY[t] === s.type) ?? TABS[0];
              const tone = TAB_TONE[tab];
              return (
                <tr key={s.type} style={{ borderTop: '1px solid var(--line-soft)' }}>
                  <td style={{ padding: '12px 16px', fontWeight: 700, color: 'var(--ink-900)' }}>
                    <Chip tone={tone.chip as 'green'|'info'|'warm'} size="sm">{s.type_label}</Chip>
                  </td>
                  <td className="num" style={{ padding: '12px 16px', color: 'var(--ink-700)' }}>{s.senior_count}명</td>
                  <td className="num" style={{ padding: '12px 16px', color: 'var(--ink-700)' }}>{fmt(s.total_budget)}원</td>
                  <td className="num" style={{ padding: '12px 16px', color: 'var(--ink-700)' }}>{fmt(s.total_expenditure)}원</td>
                  <td className="num" style={{ padding: '12px 16px', color: s.remaining >= 0 ? 'var(--green-700)' : 'var(--danger)', fontWeight: 700 }}>{fmt(s.remaining)}원</td>
                  <td style={{ padding: '12px 16px', minWidth: 140 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ flex: 1 }}>
                        <Progress value={Math.min(s.achievement_rate, 100)} color={s.achievement_rate > 90 ? 'var(--danger)' : tone.color} height={6}/>
                      </div>
                      <span className="num" style={{ fontSize: 12, fontWeight: 700, color: s.achievement_rate > 90 ? 'var(--danger)' : 'var(--ink-700)' }}>{Math.round(s.achievement_rate)}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </>
  );
}

import { useState, useEffect } from 'react';
import type { TabType } from '../types';
import { useBusinessUnits } from '../hooks/useBusinessUnits';
import { useAppStore } from '../stores/appStore';
import { api } from '../lib/api';
import { UnitTabBar } from '../components/layout/UnitTabBar';
import { AlertBox } from '../components/layout/AlertBox';
import { Card } from '../components/layout/Card';
import { Chip } from '../components/shared/Chip';
import { Button } from '../components/shared/Button';
import { Icons } from '../components/shared/Icons';

interface WorkLogProps {
  tab: TabType;
  setTab: (t: TabType) => void;
  year: number;
  month: number;
}

interface CaseRow {
  row_count: number;
  count: number;
}

interface PrintListData {
  seniors: { senior_id: string; name: string; workplace: string; row_count: number; business_unit_name: string }[];
  case_summary: Record<string, number>;
  total_pages: number;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function WorkLog({ tab, setTab, year, month }: WorkLogProps) {
  const storeYear = useAppStore((s) => s.year);
  const { units, byTab } = useBusinessUnits(storeYear);
  const bu = byTab(tab);

  const [step, setStep] = useState(1);
  const [format, setFormat] = useState<'excel' | 'print' | null>(null);
  const [selectedRows, setSelectedRows] = useState<number | null>(null);
  const [printData, setPrintData] = useState<PrintListData | null>(null);
  const [loadingData, setLoadingData] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const availableTabs = units.map((u) => {
    if (u.type === 'public_benefit') return '공익활동형' as TabType;
    if (u.type === 'social_service') return '사회서비스형' as TabType;
    return '시장형' as TabType;
  });

  useEffect(() => {
    if (step !== 1) return;
    setLoadingData(true);
    const params: Record<string, string | number> = { year, month };
    if (bu?.id) params.business_unit_id = bu.id;
    api.get<PrintListData>(`/work-logs/print-list/${year}/${month}`, { params })
      .then((r) => {
        setPrintData(r.data);
        const keys = Object.keys(r.data.case_summary);
        if (keys.length > 0) setSelectedRows(parseInt(keys[0].replace('행', ''), 10));
      })
      .catch(() => setPrintData(null))
      .finally(() => setLoadingData(false));
  }, [year, month, bu?.id, step]);

  const cases: CaseRow[] = printData
    ? Object.entries(printData.case_summary).map(([k, v]) => ({ row_count: parseInt(k.replace('행', ''), 10), count: v }))
    : [];

  const total = cases.reduce((s, c) => s + c.count, 0);
  const totalSheets = total;

  const goBack = () => {
    if (step === 1) return;
    if (step === 3) { setStep(1); setFormat(null); return; }
    setStep(step - 1);
  };

  const handleExcelDownload = async () => {
    setDownloading(true);
    try {
      const params = new URLSearchParams({ year: String(year), month: String(month) });
      if (bu?.id) params.append('business_unit_id', bu.id);
      const token = localStorage.getItem('access_token') ?? '';
      const r = await fetch(`/api/v1/work-logs/export/excel/${year}/${month}?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error('download failed');
      const blob = await r.blob();
      downloadBlob(blob, `work_log_${year}_${String(month).padStart(2, '0')}.xlsx`);
    } catch {
      alert('Excel 다운로드에 실패했습니다.');
    } finally {
      setDownloading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const STEPS = [
    { n: 1, label: '출력 목록 확인' },
    { n: 2, label: '형식 선택' },
    { n: 3, label: '출력 실행' },
  ];

  return (
    <>
      {/* Step indicator */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, marginBottom: 24 }}>
        {STEPS.map((s, i) => (
          <div key={s.n} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: '50%',
                background: step >= s.n ? 'var(--green-700)' : 'var(--cream-100)',
                color: step >= s.n ? '#fff' : 'var(--ink-500)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 15, fontWeight: 800,
              }}>{step > s.n ? '✓' : s.n}</div>
              <div style={{ fontSize: 15, fontWeight: step === s.n ? 800 : 500, color: step === s.n ? 'var(--ink-900)' : 'var(--ink-500)' }}>{s.label}</div>
            </div>
            {i < STEPS.length - 1 && <div style={{ width: 60, height: 2, background: step > s.n ? 'var(--green-700)' : 'var(--line)' }}/>}
          </div>
        ))}
      </div>

      <UnitTabBar tab={tab} onChange={setTab} availableTabs={availableTabs} right={
        step !== 1 ? <Button variant="ghost" size="sm" onClick={goBack}>← 이전 단계</Button> : undefined
      }/>

      {/* STEP 1 */}
      {step === 1 && (
        <>
          <AlertBox tone="info">
            이번 달 어르신 전체 목록이 자동 생성됐습니다. 출력 장수는 행 수 케이스별로 자동 집계됩니다.
          </AlertBox>

          <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 20 }}>
            <Card title="행수별 집계" padding="0">
              {loadingData ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)' }}>로딩 중…</div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
                  <thead>
                    <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
                      {['행수', '어르신 수', '출력 장수'].map((h) => (
                        <th key={h} style={{ padding: '12px 18px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {cases.length === 0 && (
                      <tr><td colSpan={3} style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)' }}>데이터가 없습니다.</td></tr>
                    )}
                    {cases.map((c) => (
                      <tr key={c.row_count} onClick={() => setSelectedRows(c.row_count)} style={{ borderTop: '1px solid var(--line-soft)', cursor: 'pointer', background: selectedRows === c.row_count ? 'var(--green-50)' : '#fff' }}>
                        <td style={{ padding: '14px 18px' }}>
                          <Chip tone={selectedRows === c.row_count ? 'green' : 'neutral'} size="sm">{c.row_count}행</Chip>
                        </td>
                        <td className="num" style={{ padding: '14px 18px', fontWeight: 700, color: 'var(--ink-900)' }}>{c.count}명</td>
                        <td className="num" style={{ padding: '14px 18px', fontWeight: 600 }}>{c.count}장</td>
                      </tr>
                    ))}
                    <tr style={{ background: 'var(--cream-50)', borderTop: '2px solid var(--line)', fontWeight: 800 }}>
                      <td style={{ padding: '14px 18px' }}>합계</td>
                      <td className="num" style={{ padding: '14px 18px', color: 'var(--green-700)' }}>{total}명</td>
                      <td className="num" style={{ padding: '14px 18px', color: 'var(--green-700)' }}>{totalSheets}장</td>
                    </tr>
                  </tbody>
                </table>
              )}
            </Card>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--ink-900)' }}>📋 근무일지 미리보기 ({selectedRows ?? '—'}행)</div>
                <Chip tone="green" size="sm">A4 가로</Chip>
              </div>
              <div style={{ background: '#fff', border: '2px solid var(--line)', borderRadius: 14, overflow: 'hidden' }}>
                <div style={{ background: 'var(--green-700)', color: '#fff', padding: '10px 14px', textAlign: 'center', fontSize: 14, fontWeight: 700 }}>
                  {year}년도 노인일자리 근무일지
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: 'var(--cream-50)' }}>
                      {[['날짜',50],['성명',70],['근무장소',0],['일한시간',60],['담당자 (인)',70],['사회복지사 (인)',80]].map(([h, w]) => (
                        <th key={h as string} style={{ padding: '8px 6px', fontWeight: 700, color: 'var(--ink-700)', textAlign: 'center', border: '1px solid var(--line)', width: (w as number) || 'auto' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Array.from({ length: selectedRows ?? 10 }).map((_, i) => (
                      <tr key={i}>
                        <td style={{ padding: '9px 6px', textAlign: 'center', color: 'var(--ink-500)', border: '1px solid var(--line)' }}>/</td>
                        <td style={{ padding: '9px 6px', border: '1px solid var(--line)' }}></td>
                        <td style={{ padding: '9px 6px', border: '1px solid var(--line)' }}></td>
                        <td style={{ padding: '9px 6px', border: '1px solid var(--line)' }}></td>
                        <td style={{ padding: '9px 6px', textAlign: 'center', color: 'var(--ink-500)', border: '1px solid var(--line)' }}>(인)</td>
                        <td style={{ padding: '9px 6px', textAlign: 'center', color: 'var(--ink-500)', border: '1px solid var(--line)' }}>(인)</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <AlertBox tone="warn">
                기관서명·담당사복사 <strong>"(인)"</strong> 표기는 위조 방지를 위해 자동 인쇄됩니다.
              </AlertBox>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 22 }}>
            <Button variant="ghost" size="md" onClick={() => setStep(1)}>취소</Button>
            <Button variant="primary" size="md" icon={<Icons.arrow/>} onClick={() => setStep(2)}>출력하기 ({totalSheets}장)</Button>
          </div>
        </>
      )}

      {/* STEP 2 */}
      {step === 2 && (
        <div style={{ maxWidth: 760, margin: '20px auto 0' }}>
          <h2 style={{ fontSize: 24, fontWeight: 800, color: 'var(--ink-900)', textAlign: 'center', marginBottom: 8 }}>출력 형식을 선택하세요</h2>
          <p style={{ fontSize: 15, color: 'var(--ink-500)', textAlign: 'center', marginBottom: 32 }}>
            선택 즉시 전체 <strong>{totalSheets}장</strong>이 처리됩니다.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
            {[
              { id: 'excel' as const, emoji: '📊', title: 'Excel로 저장', sub: '.xlsx 1개 파일', color: 'var(--green-700)', desc: '전체 어르신 시트가 담긴 .xlsx 1개 다운로드. 어르신 1인 = 1페이지 보장.' },
              { id: 'print' as const, emoji: '🖨️', title: '인쇄',          sub: '프린터 즉시 출력', color: 'var(--info)',      desc: '브라우저 인쇄 다이얼로그 1회 호출 → 지정 장수 전체 인쇄.' },
            ].map((f) => (
              <div key={f.id} onClick={() => { setFormat(f.id); setStep(3); }} style={{
                background: '#fff', border: `1.5px solid var(--line)`, borderRadius: 20,
                padding: '32px 28px', cursor: 'pointer', boxShadow: 'var(--shadow-sm)', textAlign: 'center',
              }}>
                <div style={{ fontSize: 56, marginBottom: 14 }}>{f.emoji}</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--ink-900)' }}>{f.title}</div>
                <div style={{ fontSize: 14, color: f.color, fontWeight: 700, marginTop: 4 }}>{f.sub}</div>
                <div style={{ fontSize: 14, color: 'var(--ink-500)', marginTop: 14, lineHeight: 1.6 }}>{f.desc}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 28, textAlign: 'center' }}>
            <Button variant="ghost" size="md" onClick={() => setStep(1)}>← 목록으로 돌아가기</Button>
          </div>
        </div>
      )}

      {/* STEP 3 */}
      {step === 3 && (
        <div style={{ maxWidth: 600, margin: '60px auto', textAlign: 'center' }}>
          <div style={{ width: 96, height: 96, borderRadius: '50%', background: 'var(--green-100)', color: 'var(--green-700)', margin: '0 auto 24px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 48 }}>
            {format === 'excel' ? '📥' : '🖨️'}
          </div>
          <h2 style={{ fontSize: 28, fontWeight: 800, color: 'var(--ink-900)', margin: '0 0 12px' }}>
            {format === 'excel' ? 'Excel 다운로드' : '인쇄'}
          </h2>
          <p style={{ fontSize: 16, color: 'var(--ink-500)', lineHeight: 1.6, marginBottom: 32 }}>
            {format === 'excel'
              ? <>work_log_{year}_{String(month).padStart(2,'0')}.xlsx · 전체 <strong>{totalSheets}명</strong> 어르신 시트 포함</>
              : <>브라우저 인쇄 창이 열립니다. 전체 <strong>{totalSheets}장</strong>을 인쇄합니다.</>
            }
          </p>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 8 }}>
            <Button variant="secondary" size="md" onClick={() => setStep(1)}>← 돌아가기</Button>
            {format === 'excel' ? (
              <Button variant="primary" size="md" icon={<Icons.download/>} onClick={handleExcelDownload}
                disabled={downloading}>
                {downloading ? '다운로드 중…' : 'Excel 다운로드'}
              </Button>
            ) : (
              <Button variant="primary" size="md" icon={<Icons.doc/>} onClick={handlePrint}>
                인쇄 창 열기
              </Button>
            )}
          </div>
        </div>
      )}
    </>
  );
}

import { useState } from 'react';
import type { TabType } from '../types';
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

const CASES = [
  { r: 10, n: 45, note: '1~6월 기본' },
  { r: 11, n: 23, note: '이월 반영' },
  { r: 12, n: 18, note: '이월 반영' },
  { r: 14, n: 5,  note: '소진 임박' },
];

export function WorkLog({ tab, setTab, year, month }: WorkLogProps) {
  const [step, setStep] = useState(1);
  const [format, setFormat] = useState<'excel'|'print'|null>(null);
  const [selectedRows, setSelectedRows] = useState(10);

  const total = CASES.reduce((s, c) => s + c.n, 0);
  const totalSheets = CASES.reduce((s, c) => s + c.n, 0);

  const goBack = () => {
    if (step === 1) return;
    if (step === 3) { setStep(1); setFormat(null); return; }
    setStep(step - 1);
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

      <UnitTabBar tab={tab} onChange={setTab} right={
        step !== 1 ? <Button variant="ghost" size="sm" onClick={goBack}>← 이전 단계</Button> : undefined
      }/>

      {/* STEP 1 */}
      {step === 1 && (
        <>
          <AlertBox tone="info">
            이번 달 어르신 전체 목록이 자동 생성됐습니다. 출력 장수는 행 수 케이스별로 자동 집계되며, 필요 시 직접 수정할 수 있습니다.
          </AlertBox>

          <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 20 }}>
            <Card title="행수별 집계" padding="0">
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
                <thead>
                  <tr style={{ background: 'var(--cream-50)', textAlign: 'left' }}>
                    {['행수', '어르신 수', '출력 장수', '비고'].map((h) => (
                      <th key={h} style={{ padding: '12px 18px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {CASES.map((c) => (
                    <tr key={c.r} onClick={() => setSelectedRows(c.r)} style={{ borderTop: '1px solid var(--line-soft)', cursor: 'pointer', background: selectedRows === c.r ? 'var(--green-50)' : '#fff' }}>
                      <td style={{ padding: '14px 18px' }}>
                        <Chip tone={selectedRows === c.r ? 'green' : 'neutral'} size="sm">{c.r}행</Chip>
                      </td>
                      <td className="num" style={{ padding: '14px 18px', fontWeight: 700, color: 'var(--ink-900)' }}>{c.n}명</td>
                      <td style={{ padding: '14px 18px' }}>
                        <input defaultValue={c.n} style={{ width: 70, padding: '8px 12px', border: '1.5px solid var(--line)', borderRadius: 8, textAlign: 'center', fontSize: 14, outline: 'none' }}/>
                        <span style={{ fontSize: 13, color: 'var(--ink-500)', marginLeft: 6 }}>장</span>
                      </td>
                      <td style={{ padding: '14px 18px', fontSize: 13, color: 'var(--ink-500)' }}>{c.note}</td>
                    </tr>
                  ))}
                  <tr style={{ background: 'var(--cream-50)', borderTop: '2px solid var(--line)', fontWeight: 800 }}>
                    <td style={{ padding: '14px 18px' }}>합계</td>
                    <td className="num" style={{ padding: '14px 18px', color: 'var(--green-700)' }}>{total}명</td>
                    <td className="num" style={{ padding: '14px 18px', color: 'var(--green-700)' }}>{totalSheets}장</td>
                    <td/>
                  </tr>
                </tbody>
              </table>
            </Card>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--ink-900)' }}>📋 근무일지 미리보기 ({selectedRows}행)</div>
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
                    {Array.from({ length: selectedRows }).map((_, i) => (
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
                <div style={{ padding: '8px 14px', fontSize: 11, color: 'var(--ink-500)', borderTop: '1px solid var(--line)', textAlign: 'right' }}>
                  ※ 날짜·성함·근무장소는 어르신이 직접 기재 / 서명란 "(인)" = 위조 방지 자동 인쇄
                </div>
              </div>
              <AlertBox tone="warn">
                기관서명·담당사복사 <strong>"(인)"</strong> 표기는 위조 방지를 위해 자동 인쇄됩니다.
              </AlertBox>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 22 }}>
            <Button variant="ghost" size="md">취소</Button>
            <Button variant="primary" size="md" icon={<Icons.arrow/>} onClick={() => setStep(2)}>출력하기 ({totalSheets}장)</Button>
          </div>
        </>
      )}

      {/* STEP 2 */}
      {step === 2 && (
        <div style={{ maxWidth: 760, margin: '20px auto 0' }}>
          <h2 style={{ fontSize: 24, fontWeight: 800, color: 'var(--ink-900)', textAlign: 'center', marginBottom: 8 }}>출력 형식을 선택하세요</h2>
          <p style={{ fontSize: 15, color: 'var(--ink-500)', textAlign: 'center', marginBottom: 32 }}>
            선택 즉시 전체 <strong>{totalSheets}장</strong>이 처리됩니다. (추가 확인 없음)
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
            {format === 'excel' ? 'Excel 다운로드 완료' : '인쇄 작업 전송 완료'}
          </h2>
          <p style={{ fontSize: 16, color: 'var(--ink-500)', lineHeight: 1.6, marginBottom: 32 }}>
            {format === 'excel'
              ? <>worklog_{year}_{month}.xlsx · 전체 <strong>{totalSheets}명</strong> 어르신 시트 포함</>
              : <>프린터로 전체 <strong>{totalSheets}장</strong>이 전송됐습니다.</>
            }
          </p>
          <div style={{ background: '#fff', border: '1px solid var(--line)', borderRadius: 16, padding: '22px 24px', textAlign: 'left' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-500)', marginBottom: 12 }}>출력 요약</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[
                ['사업단', tab],
                ['출력 형식', format === 'excel' ? 'Excel (.xlsx)' : '프린터 인쇄'],
                ['연월', `${year}년 ${month}월`],
                ['총 인원/장수', `${total}명 / ${totalSheets}장`],
              ].map(([l, v]) => (
                <div key={l} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, padding: '8px 0', borderBottom: '1px solid var(--line-soft)' }}>
                  <span style={{ color: 'var(--ink-500)' }}>{l}</span>
                  <span style={{ fontWeight: 700, color: 'var(--ink-900)' }}>{v}</span>
                </div>
              ))}
            </div>
            <div style={{ fontSize: 12, color: 'var(--ink-400)', marginTop: 12, fontFamily: 'var(--font-mono)' }}>
              📁 document_snapshots에 자동 저장됨
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 28 }}>
            <Button variant="secondary" size="md" onClick={() => setStep(1)}>다시 출력</Button>
            <Button variant="primary" size="md">대시보드로 →</Button>
          </div>
        </div>
      )}
    </>
  );
}

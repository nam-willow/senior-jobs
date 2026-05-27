import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { useAuthStore } from '../stores/authStore';
import { useBusinessUnits } from '../hooks/useBusinessUnits';
import { useAppStore } from '../stores/appStore';
import { Card } from '../components/layout/Card';
import { Button } from '../components/shared/Button';
import { Chip } from '../components/shared/Chip';
import { Modal } from '../components/layout/Modal';
import { Icons } from '../components/shared/Icons';

interface Staff {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
}

const ROLE_LABEL: Record<string, string> = {
  tenant_admin: '관리자',
  social_worker: '사회복지사',
};

const BIZ_LABEL: Record<string, string> = {
  public_benefit: '공익활동형', social_service: '사회서비스형', market: '시장형',
};

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 13px', border: '1.5px solid var(--line)',
  borderRadius: 10, fontSize: 14, outline: 'none', background: '#fff',
  color: 'var(--ink-900)', boxSizing: 'border-box', fontFamily: 'inherit',
};
const labelStyle: React.CSSProperties = {
  fontSize: 13, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 5, display: 'block',
};

export function Settings() {
  const year = useAppStore((s) => s.year);
  const { units, loading: uLoading, refetch: refetchBiz } = useBusinessUnits(year);
  const [section, setSection] = useState<'staff' | 'business' | 'admin'>('staff');

  // ── 직원 목록 ──────────────────────────────────────────────────────────────
  const [staffList, setStaffList] = useState<Staff[]>([]);
  const [staffLoading, setStaffLoading] = useState(false);
  const fetchStaff = () => {
    setStaffLoading(true);
    api.get<{ items: Staff[] }>('/users/')
      .then((r) => setStaffList(r.data.items))
      .catch(() => setStaffList([]))
      .finally(() => setStaffLoading(false));
  };
  useEffect(() => { if (section === 'staff' || section === 'admin') fetchStaff(); }, [section]);

  // ── 직원 추가 모달 ─────────────────────────────────────────────────────────
  const [addOpen, setAddOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('social_worker');
  const [addError, setAddError] = useState('');
  const [addLoading, setAddLoading] = useState(false);

  const handleAddStaff = async () => {
    setAddError('');
    if (!newName.trim()) { setAddError('이름을 입력해주세요.'); return; }
    if (!newEmail.trim()) { setAddError('이메일을 입력해주세요.'); return; }
    if (newPassword.length < 8) { setAddError('비밀번호는 8자 이상이어야 합니다.'); return; }
    setAddLoading(true);
    try {
      await api.post('/users/', { name: newName, email: newEmail, password: newPassword, role: newRole, business_unit_ids: [] });
      setAddOpen(false);
      setNewName(''); setNewEmail(''); setNewPassword(''); setNewRole('social_worker');
      fetchStaff();
    } catch (err: any) {
      setAddError(err?.response?.data?.detail ?? '오류가 발생했습니다.');
    } finally {
      setAddLoading(false);
    }
  };

  const handleDeactivate = async (id: string, name: string) => {
    if (!confirm(`${name} 직원을 비활성화하시겠습니까?`)) return;
    try {
      await api.patch(`/users/${id}/deactivate`);
      fetchStaff();
    } catch (err: any) {
      alert(err?.response?.data?.detail ?? '비활성화 중 오류가 발생했습니다.');
    }
  };

  // ── 사업단 추가 모달 ────────────────────────────────────────────────────────
  const [bizOpen, setBizOpen] = useState(false);
  const [bizType, setBizType] = useState('public_benefit');
  const [bizLoading, setBizLoading] = useState(false);
  const [bizError, setBizError] = useState('');
  // 시장형 전용 필드
  const [mktMonthlyDefault, setMktMonthlyDefault] = useState('');
  const [mktMonthlyMax, setMktMonthlyMax] = useState('');
  const [mktAnnualTotal, setMktAnnualTotal] = useState('');
  const [mktSessionDefault, setMktSessionDefault] = useState('');

  const resetBizForm = () => {
    setBizType('public_benefit');
    setBizError('');
    setMktMonthlyDefault(''); setMktMonthlyMax('');
    setMktAnnualTotal(''); setMktSessionDefault('');
  };

  const handleAddBiz = async () => {
    setBizError('');
    if (bizType === 'market') {
      if (!mktMonthlyDefault || !mktMonthlyMax || !mktAnnualTotal || !mktSessionDefault) {
        setBizError('시장형은 모든 근무시간 항목을 입력해야 합니다.');
        return;
      }
    }
    setBizLoading(true);
    try {
      const payload: Record<string, unknown> = {
        name: BIZ_LABEL[bizType] ?? bizType,
        type: bizType,
        year,
      };
      if (bizType === 'market') {
        payload.monthly_default_hours = parseInt(mktMonthlyDefault, 10);
        payload.monthly_max_hours     = parseInt(mktMonthlyMax, 10);
        payload.total_annual_hours    = parseInt(mktAnnualTotal, 10);
        payload.session_default_hours = parseInt(mktSessionDefault, 10);
      }
      await api.post('/business-units/', payload);
      setBizOpen(false);
      resetBizForm();
      refetchBiz();
    } catch (err: any) {
      setBizError(err?.response?.data?.detail ?? '오류가 발생했습니다.');
    } finally {
      setBizLoading(false);
    }
  };

  const handleDeleteBiz = async (id: string, name: string) => {
    if (!confirm(`"${name}" 사업단을 삭제하시겠습니까?\n(지출 내역이 있으면 삭제할 수 없습니다.)`)) return;
    try {
      await api.delete(`/business-units/${id}`);
      refetchBiz();
    } catch (err: any) {
      alert(err?.response?.data?.detail ?? '삭제 중 오류가 발생했습니다.');
    }
  };

  // ── 관리자 권한 이전 ────────────────────────────────────────────────────────
  const [transferTarget, setTransferTarget] = useState('');
  const [transferLoading, setTransferLoading] = useState(false);
  const [transferError, setTransferError] = useState('');
  const [transferDone, setTransferDone] = useState(false);
  const activeStaff = staffList.filter((s) => s.is_active && s.role !== 'tenant_admin');

  const handleTransfer = async () => {
    if (!transferTarget) { setTransferError('이전받을 직원을 선택해주세요.'); return; }
    if (!confirm('관리자 권한을 이전하면 본인은 일반 직원으로 변경됩니다. 계속하시겠습니까?')) return;
    setTransferLoading(true);
    setTransferError('');
    try {
      await api.post('/users/transfer-admin', { target_user_id: transferTarget });
      setTransferDone(true);
      useAuthStore.getState().logout();
    } catch (err: any) {
      setTransferError(err?.response?.data?.detail ?? '오류가 발생했습니다.');
    } finally {
      setTransferLoading(false);
    }
  };

  const tabs = [
    { id: 'staff', label: '직원 관리' },
    { id: 'business', label: '사업단 관리' },
    { id: 'admin', label: '관리자 권한 이전' },
  ] as const;

  return (
    <>
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {tabs.map((t) => (
          <div key={t.id} onClick={() => setSection(t.id)} style={{
            padding: '10px 20px', borderRadius: 10, cursor: 'pointer',
            fontSize: 15, fontWeight: section === t.id ? 700 : 500,
            background: section === t.id ? 'var(--green-700)' : '#fff',
            color: section === t.id ? '#fff' : 'var(--ink-700)',
            border: '1.5px solid var(--line)',
          }}>
            {t.label}
          </div>
        ))}
      </div>

      {/* ── 직원 관리 ── */}
      {section === 'staff' && (
        <Card title="직원 목록" right={
          <Button variant="primary" size="sm" icon={<Icons.plus/>} onClick={() => { setAddError(''); setAddOpen(true); }}>직원 추가</Button>
        } padding="0">
          {staffLoading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)' }}>로딩 중…</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
              <thead>
                <tr style={{ background: 'var(--cream-50)' }}>
                  {['이름', '이메일', '역할', '상태', ''].map((h) => (
                    <th key={h} style={{ padding: '13px 20px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, textAlign: 'left' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {staffList.map((s) => (
                  <tr key={s.id} style={{ borderTop: '1px solid var(--line-soft)' }}>
                    <td style={{ padding: '14px 20px', fontWeight: 700, color: 'var(--ink-900)' }}>{s.name}</td>
                    <td style={{ padding: '14px 20px', color: 'var(--ink-700)' }}>{s.email}</td>
                    <td style={{ padding: '14px 20px' }}>
                      <Chip tone={s.role === 'tenant_admin' ? 'green' : 'neutral'} size="sm">
                        {ROLE_LABEL[s.role] ?? s.role}
                      </Chip>
                    </td>
                    <td style={{ padding: '14px 20px' }}>
                      <Chip tone={s.is_active ? 'green' : 'danger'} size="sm">
                        {s.is_active ? '활성' : '비활성'}
                      </Chip>
                    </td>
                    <td style={{ padding: '14px 20px' }}>
                      {s.is_active && s.role !== 'tenant_admin' && (
                        <Button variant="ghost" size="sm" onClick={() => handleDeactivate(s.id, s.name)}>
                          비활성화
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
                {staffList.length === 0 && (
                  <tr><td colSpan={5} style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)' }}>
                    등록된 직원이 없습니다.
                  </td></tr>
                )}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {/* ── 사업단 관리 ── */}
      {section === 'business' && (
        <Card title="사업단 목록" right={
          <Button variant="primary" size="sm" icon={<Icons.plus/>} onClick={() => { resetBizForm(); setBizOpen(true); }}>사업단 추가</Button>
        } padding="0">
          {uLoading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)' }}>로딩 중…</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
              <thead>
                <tr style={{ background: 'var(--cream-50)' }}>
                  {['사업 유형', '연도', '기본시간/월', '최대시간/월', '상태', ''].map((h) => (
                    <th key={h} style={{ padding: '13px 20px', fontWeight: 700, color: 'var(--ink-500)', fontSize: 13, textAlign: 'left' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {units.map((u) => (
                  <tr key={u.id} style={{ borderTop: '1px solid var(--line-soft)' }}>
                    <td style={{ padding: '14px 20px', fontWeight: 700, color: 'var(--ink-900)' }}>
                      {BIZ_LABEL[u.type] ?? u.type}
                    </td>
                    <td style={{ padding: '14px 20px', color: 'var(--ink-700)' }}>{u.year}년</td>
                    <td className="num" style={{ padding: '14px 20px', color: 'var(--ink-700)' }}>{u.monthly_default_hours}h</td>
                    <td className="num" style={{ padding: '14px 20px', color: 'var(--ink-700)' }}>{u.monthly_max_hours}h</td>
                    <td style={{ padding: '14px 20px' }}>
                      <Chip tone={u.is_active ? 'green' : 'danger'} size="sm">
                        {u.is_active ? '운영 중' : '비활성'}
                      </Chip>
                    </td>
                    <td style={{ padding: '14px 20px' }}>
                      {u.is_active && (
                        <Button variant="ghost" size="sm" onClick={() => handleDeleteBiz(u.id, BIZ_LABEL[u.type] ?? u.type)}>
                          삭제
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
                {units.length === 0 && (
                  <tr><td colSpan={6} style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)' }}>
                    등록된 사업단이 없습니다.
                  </td></tr>
                )}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {/* ── 관리자 권한 이전 ── */}
      {section === 'admin' && (
        <Card title="관리자 권한 이전" padding="28px 32px">
          {transferDone ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--green-700)', fontSize: 16, fontWeight: 700 }}>
              권한 이전이 완료되었습니다. 자동 로그아웃됩니다.
            </div>
          ) : (
            <div style={{ maxWidth: 420 }}>
              <div style={{ fontSize: 14, color: 'var(--ink-500)', marginBottom: 20, lineHeight: 1.7 }}>
                관리자 권한을 이전하면 <strong>본인 계정은 사회복지사로 변경</strong>되고,
                선택한 직원이 새 관리자가 됩니다. 이 작업은 되돌릴 수 없습니다.
              </div>
              <label style={labelStyle}>이전받을 직원 선택</label>
              <select value={transferTarget} onChange={(e) => setTransferTarget(e.target.value)} style={{ ...inputStyle, marginBottom: 16 }}>
                <option value="">-- 직원 선택 --</option>
                {activeStaff.map((s) => (
                  <option key={s.id} value={s.id}>{s.name} ({s.email})</option>
                ))}
              </select>
              {activeStaff.length === 0 && (
                <div style={{ fontSize: 13, color: 'var(--ink-400)', marginBottom: 12 }}>
                  권한을 이전할 수 있는 활성 직원이 없습니다.
                </div>
              )}
              {transferError && <ErrorBox>{transferError}</ErrorBox>}
              <Button variant="primary" size="md" onClick={handleTransfer} disabled={transferLoading || !transferTarget}>
                {transferLoading ? '처리 중…' : '관리자 권한 이전'}
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* ── 직원 추가 모달 ── */}
      {addOpen && (
        <Modal open onClose={() => setAddOpen(false)} width={480}>
          <div style={{ padding: '28px 32px' }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--ink-900)', marginBottom: 24 }}>직원 추가</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {[
                { label: '이름', value: newName, set: setNewName, type: 'text', placeholder: '홍길동' },
                { label: '이메일', value: newEmail, set: setNewEmail, type: 'email', placeholder: 'staff@welfare.org' },
                { label: '임시 비밀번호 (8자 이상)', value: newPassword, set: setNewPassword, type: 'password', placeholder: '••••••••' },
              ].map((f) => (
                <div key={f.label}>
                  <label style={labelStyle}>{f.label}</label>
                  <input type={f.type} value={f.value} onChange={(e) => f.set(e.target.value)}
                    placeholder={f.placeholder} style={inputStyle}/>
                </div>
              ))}
              <div>
                <label style={labelStyle}>역할</label>
                <select value={newRole} onChange={(e) => setNewRole(e.target.value)} style={inputStyle}>
                  <option value="social_worker">사회복지사</option>
                </select>
              </div>
            </div>
            {addError && <ErrorBox style={{ marginTop: 14 }}>{addError}</ErrorBox>}
            <div style={{ display: 'flex', gap: 10, marginTop: 24, justifyContent: 'flex-end' }}>
              <Button variant="ghost" size="md" onClick={() => setAddOpen(false)}>취소</Button>
              <Button variant="primary" size="md" onClick={handleAddStaff} disabled={addLoading}>
                {addLoading ? '추가 중…' : '직원 추가'}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ── 사업단 추가 모달 ── */}
      {bizOpen && (
        <Modal open onClose={() => { setBizOpen(false); resetBizForm(); }} width={460}>
          <div style={{ padding: '28px 32px' }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--ink-900)', marginBottom: 24 }}>사업단 추가</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={labelStyle}>사업 유형</label>
                <select value={bizType} onChange={(e) => { setBizType(e.target.value); setBizError(''); }} style={inputStyle}>
                  <option value="public_benefit">공익활동형</option>
                  <option value="social_service">사회서비스형</option>
                  <option value="market">시장형</option>
                </select>
              </div>

              {/* 공익/사회서비스형: 기준 안내 */}
              {bizType !== 'market' && (
                <div style={{ background: 'var(--green-50)', border: '1px solid var(--green-200)', borderRadius: 10, padding: '12px 14px', fontSize: 13, color: 'var(--ink-600)' }}>
                  {bizType === 'public_benefit'
                    ? '기본 30h/월, 최대 42h/월, 연간 330h (정책 기준 자동 적용)'
                    : '기본 60h/월, 최대 60h/월, 연간 660h (정책 기준 자동 적용)'}
                </div>
              )}

              {/* 시장형: 직접 입력 */}
              {bizType === 'market' && (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    {[
                      { label: '기본 근무시간/월 (h)', value: mktMonthlyDefault, set: setMktMonthlyDefault },
                      { label: '최대 근무시간/월 (h)', value: mktMonthlyMax,     set: setMktMonthlyMax     },
                      { label: '연간 총 근무시간 (h)',  value: mktAnnualTotal,    set: setMktAnnualTotal    },
                      { label: '기본 세션시간 (h)',     value: mktSessionDefault, set: setMktSessionDefault },
                    ].map((f) => (
                      <div key={f.label}>
                        <label style={labelStyle}>{f.label}</label>
                        <input type="number" min="1" value={f.value}
                          onChange={(e) => f.set(e.target.value)} placeholder="0" style={inputStyle}/>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>
                    시장형은 사업 특성에 따라 직접 입력합니다.
                  </div>
                </>
              )}
            </div>

            {bizError && <ErrorBox style={{ marginTop: 14 }}>{bizError}</ErrorBox>}

            <div style={{ display: 'flex', gap: 10, marginTop: 24, justifyContent: 'flex-end' }}>
              <Button variant="ghost" size="md" onClick={() => { setBizOpen(false); resetBizForm(); }}>취소</Button>
              <Button variant="primary" size="md" onClick={handleAddBiz} disabled={bizLoading}>
                {bizLoading ? '추가 중…' : '사업단 추가'}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}

function ErrorBox({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: '#FBE3E3', border: '1px solid var(--danger)', borderRadius: 8,
      padding: '10px 14px', fontSize: 13, color: 'var(--danger)', ...style,
    }}>
      {children}
    </div>
  );
}

import { useState } from 'react';
import { api } from '../lib/api';
import { Logo } from '../components/shared/Logo';

type BizType = 'public_benefit' | 'social_service' | 'market';

const BIZ_LABELS: Record<BizType, string> = {
  public_benefit: '공익활동형',
  social_service: '사회서비스형',
  market: '시장형',
};

interface RegisterProps {
  onRegistered: () => void;
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '11px 14px', border: '1.5px solid var(--line)',
  borderRadius: 10, fontSize: 15, outline: 'none', boxSizing: 'border-box',
  fontFamily: 'inherit', background: '#fff',
};

export function Register({ onRegistered }: RegisterProps) {
  const [tenantName, setTenantName] = useState('');
  const [tenantAddress, setTenantAddress] = useState('');
  const [bizTypes, setBizTypes] = useState<BizType[]>([]);
  const [adminName, setAdminName] = useState('');
  const [adminEmail, setAdminEmail] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [adminPasswordConfirm, setAdminPasswordConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const toggleType = (t: BizType) => {
    setBizTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (bizTypes.length === 0) { setError('사업 유형을 최소 1개 선택해주세요.'); return; }
    if (adminPassword !== adminPasswordConfirm) { setError('비밀번호가 일치하지 않습니다.'); return; }
    if (adminPassword.length < 8) { setError('비밀번호는 8자 이상이어야 합니다.'); return; }

    setLoading(true);
    try {
      await api.post('/register', {
        tenant_name: tenantName,
        tenant_address: tenantAddress,
        business_types: bizTypes,
        admin_name: adminName,
        admin_email: adminEmail,
        admin_password: adminPassword,
      });
      onRegistered();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : '등록 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--cream-50)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '40px 16px',
    }}>
      <div style={{
        background: '#fff', borderRadius: 24, padding: '48px 40px',
        border: '1px solid var(--line)', boxShadow: 'var(--shadow-sm)',
        width: '100%', maxWidth: 520,
      }}>
        <div style={{ marginBottom: 32, textAlign: 'center' }}>
          <Logo />
          <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--ink-900)', marginTop: 16 }}>기관 등록</div>
          <div style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 6 }}>
            처음 이용하시는 경우 기관 정보와 관리자 계정을 등록해주세요.
          </div>
        </div>

        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>

          {/* 기관 정보 섹션 */}
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--green-700)', borderBottom: '1px solid var(--line-soft)', paddingBottom: 8 }}>
            기관 정보
          </div>

          <div>
            <label style={labelStyle}>기관명 *</label>
            <input value={tenantName} onChange={(e) => setTenantName(e.target.value)}
              placeholder="예: 강남종합사회복지관" required style={inputStyle} />
          </div>

          <div>
            <label style={labelStyle}>기관 주소 *</label>
            <input value={tenantAddress} onChange={(e) => setTenantAddress(e.target.value)}
              placeholder="예: 서울시 강남구 테헤란로 123" required style={inputStyle} />
          </div>

          <div>
            <label style={labelStyle}>운영 사업 유형 * <span style={{ fontWeight: 400, color: 'var(--ink-400)' }}>(복수 선택 가능)</span></label>
            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
              {(Object.keys(BIZ_LABELS) as BizType[]).map((t) => {
                const selected = bizTypes.includes(t);
                return (
                  <div key={t} onClick={() => toggleType(t)} style={{
                    flex: 1, padding: '12px 8px', borderRadius: 12, textAlign: 'center',
                    cursor: 'pointer', fontSize: 14, fontWeight: selected ? 700 : 500,
                    border: `2px solid ${selected ? 'var(--green-600)' : 'var(--line)'}`,
                    background: selected ? 'var(--green-50)' : '#fff',
                    color: selected ? 'var(--green-700)' : 'var(--ink-500)',
                    transition: 'all 0.15s',
                  }}>
                    {selected && <span style={{ marginRight: 4 }}>✓</span>}
                    {BIZ_LABELS[t]}
                  </div>
                );
              })}
            </div>
          </div>

          {/* 관리자 계정 섹션 */}
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--green-700)', borderBottom: '1px solid var(--line-soft)', paddingBottom: 8, marginTop: 6 }}>
            관리자 계정
          </div>

          <div>
            <label style={labelStyle}>담당자 이름 *</label>
            <input value={adminName} onChange={(e) => setAdminName(e.target.value)}
              placeholder="예: 김복지" required style={inputStyle} />
          </div>

          <div>
            <label style={labelStyle}>이메일 *</label>
            <input type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)}
              placeholder="admin@welfare.org" required style={inputStyle} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>비밀번호 * <span style={{ fontWeight: 400, color: 'var(--ink-400)' }}>(8자+)</span></label>
              <input type="password" value={adminPassword} onChange={(e) => setAdminPassword(e.target.value)}
                placeholder="••••••••" required style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>비밀번호 확인 *</label>
              <input type="password" value={adminPasswordConfirm} onChange={(e) => setAdminPasswordConfirm(e.target.value)}
                placeholder="••••••••" required style={inputStyle} />
            </div>
          </div>

          {error && (
            <div style={{
              background: '#FBE3E3', border: '1px solid var(--danger)',
              borderRadius: 8, padding: '10px 14px', fontSize: 13, color: 'var(--danger)',
            }}>
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} style={{
            background: 'var(--green-700)', color: '#fff', border: 'none',
            borderRadius: 12, padding: '14px', fontSize: 16, fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1,
            marginTop: 4, fontFamily: 'inherit',
          }}>
            {loading ? '등록 중...' : '기관 등록 완료'}
          </button>

          <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--ink-500)' }}>
            이미 계정이 있으신가요?{' '}
            <span onClick={onRegistered} style={{ color: 'var(--green-700)', fontWeight: 700, cursor: 'pointer' }}>
              로그인으로 이동
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  fontSize: 13, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 6, display: 'block',
};

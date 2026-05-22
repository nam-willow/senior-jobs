import { useState } from 'react';
import { useAuthStore } from '../stores/authStore';
import { Logo } from '../components/shared/Logo';

interface LoginProps {
  onShowRegister: () => void;
}

export function Login({ onShowRegister }: LoginProps) {
  const login = useAuthStore((s) => s.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
    } catch {
      setError('이메일 또는 비밀번호가 올바르지 않습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--cream-50)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{
        background: '#fff', borderRadius: 24, padding: '48px 40px',
        border: '1px solid var(--line)', boxShadow: 'var(--shadow-sm)',
        width: '100%', maxWidth: 420,
      }}>
        <div style={{ marginBottom: 32, textAlign: 'center' }}>
          <Logo />
          <div style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 8 }}>
            노인일자리 관리 시스템
          </div>
        </div>

        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 6, display: 'block' }}>
              이메일
            </label>
            <input
              type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@example.com" required
              style={{
                width: '100%', padding: '12px 14px', border: '1.5px solid var(--line)',
                borderRadius: 10, fontSize: 15, outline: 'none', boxSizing: 'border-box',
                fontFamily: 'inherit',
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 6, display: 'block' }}>
              비밀번호
            </label>
            <input
              type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••" required
              style={{
                width: '100%', padding: '12px 14px', border: '1.5px solid var(--line)',
                borderRadius: 10, fontSize: 15, outline: 'none', boxSizing: 'border-box',
                fontFamily: 'inherit',
              }}
            />
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
            marginTop: 8, fontFamily: 'inherit',
          }}>
            {loading ? '로그인 중...' : '로그인'}
          </button>

          <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--ink-500)', marginTop: 4 }}>
            처음 이용하시나요?{' '}
            <span onClick={onShowRegister} style={{ color: 'var(--green-700)', fontWeight: 700, cursor: 'pointer' }}>
              기관 등록
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { useAppStore } from './stores/appStore';
import { useAuthStore } from './stores/authStore';
import type { PageType, TabType } from './types';
import { AdminShell } from './components/layout/AdminShell';
import { OnboardingModal } from './components/layout/OnboardingModal';
import { YearEndBudgetModal } from './components/layout/YearEndBudgetModal';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Seniors } from './pages/Seniors';
import { Work } from './pages/Work';
import { WorkLog } from './pages/WorkLog';
import { Salary } from './pages/Salary';
import { Consult } from './pages/Consult';
import { Budget } from './pages/Budget';
import { Approvals } from './pages/Approvals';
import { Alerts } from './pages/Alerts';
import { Settings } from './pages/Settings';
import { api } from './lib/api';

function App() {
  const isLoggedIn = useAuthStore((s) => s.isLoggedIn);
  const fetchMe = useAuthStore((s) => s.fetchMe);
  const { page, tab, year, month, selectedSenior, focusSenior, set } = useAppStore();

  useEffect(() => {
    if (isLoggedIn) fetchMe();
  }, [isLoggedIn]);

  // 회원가입 화면 토글
  const [showRegister, setShowRegister] = useState(false);

  // 온보딩: 사업비 미등록 여부
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [onboardingChecked, setOnboardingChecked] = useState(false);

  // 연말 사업비 모달
  const [yearEndModal, setYearEndModal] = useState<{ nextYear: number } | null>(null);
  const [skippedYears, setSkippedYears] = useState<number[]>([]);

  // 로그인 직후 사업비 등록 여부 확인
  useEffect(() => {
    if (!isLoggedIn) { setOnboardingChecked(false); setNeedsOnboarding(false); return; }
    api.get('/budgets/check', { params: { year } })
      .then((r) => { setNeedsOnboarding(!(r.data?.has_budget)); })
      .catch(() => setNeedsOnboarding(false))
      .finally(() => setOnboardingChecked(true));
  }, [isLoggedIn]);

  // 다음연도 탭 클릭 감지 (year가 현재 연도보다 1 이상 앞일 때)
  const currentRealYear = new Date().getFullYear();
  useEffect(() => {
    if (!isLoggedIn || !onboardingChecked || needsOnboarding) return;
    if (year > currentRealYear && !skippedYears.includes(year)) {
      api.get('/budgets/check', { params: { year } })
        .then((r) => { if (!r.data?.has_budget) setYearEndModal({ nextYear: year }); })
        .catch(() => {});
    }
  }, [year, isLoggedIn, onboardingChecked]);

  if (!isLoggedIn) {
    return showRegister
      ? <Register onRegistered={() => setShowRegister(false)} />
      : <Login onShowRegister={() => setShowRegister(true)} />;
  }

  if (!onboardingChecked) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--cream-50)' }}>
        <div style={{ color: 'var(--ink-400)', fontSize: 15 }}>로딩 중…</div>
      </div>
    );
  }

  if (needsOnboarding) {
    return <OnboardingModal onComplete={() => setNeedsOnboarding(false)} />;
  }

  const navigate = (p: PageType, tabVal?: TabType, seniorId?: number) => {
    set('page', p);
    if (tabVal) set('tab', tabVal);
    if (seniorId != null) set('selectedSenior', seniorId);
  };

  const renderPage = () => {
    switch (page) {
      case 'dashboard':
        return <Dashboard onNavigate={(p, t) => navigate(p, t)}/>;
      case 'seniors':
        return (
          <Seniors
            tab={tab} setTab={(t) => set('tab', t)}
            selectedSenior={selectedSenior} setSelectedSenior={(id) => set('selectedSenior', id)}
            onNavigatePage={(p) => set('page', p)} onFocusSenior={(id) => set('focusSenior', id)}
          />
        );
      case 'work':
        return <Work tab={tab} setTab={(t) => set('tab', t)} focusSenior={focusSenior} setFocusSenior={(id) => set('focusSenior', id)}/>;
      case 'worklog':
        return <WorkLog tab={tab} setTab={(t) => set('tab', t)} year={year} month={month}/>;
      case 'salary':
        return <Salary tab={tab} setTab={(t) => set('tab', t)} year={year} month={month}/>;
      case 'consult':
        return <Consult onNavigate={(p, sid) => { set('page', p); if (sid != null) set('selectedSenior', sid); }}/>;
      case 'budget':
        return <Budget tab={tab} setTab={(t) => set('tab', t)}/>;
      case 'approvals':
        return <Approvals/>;
      case 'alerts':
        return <Alerts onNavigate={(p, t, sid) => navigate(p, t, sid)}/>;
      case 'settings':
        return <Settings/>;
      default:
        return <Dashboard onNavigate={(p, t) => navigate(p, t)}/>;
    }
  };

  return (
    <>
      <AdminShell
        page={page} tab={tab} year={year} month={month}
        onNavigate={(p) => set('page', p)}
        onYearMonthChange={(y, m) => { set('year', y); set('month', m); }}
      >
        {renderPage()}
      </AdminShell>

      {yearEndModal && (
        <YearEndBudgetModal
          nextYear={yearEndModal.nextYear}
          currentYear={yearEndModal.nextYear - 1}
          onComplete={() => setYearEndModal(null)}
          onSkip={() => {
            setSkippedYears((p) => [...p, yearEndModal.nextYear]);
            setYearEndModal(null);
          }}
        />
      )}
    </>
  );
}

export default App;

import { useAppStore } from './stores/appStore';
import type { PageType, TabType } from './types';
import { AdminShell } from './components/layout/AdminShell';
import { Dashboard } from './pages/Dashboard';
import { Seniors } from './pages/Seniors';
import { Work } from './pages/Work';
import { WorkLog } from './pages/WorkLog';
import { Salary } from './pages/Salary';
import { Consult } from './pages/Consult';
import { Budget } from './pages/Budget';
import { Approvals } from './pages/Approvals';
import { Alerts } from './pages/Alerts';

function App() {
  const { page, tab, year, month, selectedSenior, focusSenior, set } = useAppStore();

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
            tab={tab}
            setTab={(t) => set('tab', t)}
            selectedSenior={selectedSenior}
            setSelectedSenior={(id) => set('selectedSenior', id)}
            onNavigatePage={(p) => set('page', p)}
            onFocusSenior={(id) => set('focusSenior', id)}
          />
        );
      case 'work':
        return (
          <Work
            tab={tab}
            setTab={(t) => set('tab', t)}
            focusSenior={focusSenior}
            setFocusSenior={(id) => set('focusSenior', id)}
          />
        );
      case 'worklog':
        return <WorkLog tab={tab} setTab={(t) => set('tab', t)} year={year} month={month}/>;
      case 'salary':
        return <Salary tab={tab} setTab={(t) => set('tab', t)} year={year} month={month}/>;
      case 'consult':
        return (
          <Consult onNavigate={(p, sid) => {
            set('page', p);
            if (sid != null) set('selectedSenior', sid);
          }}/>
        );
      case 'budget':
        return <Budget tab={tab} setTab={(t) => set('tab', t)}/>;
      case 'approvals':
        return <Approvals/>;
      case 'alerts':
        return <Alerts onNavigate={(p, t, sid) => navigate(p, t, sid)}/>;
      default:
        return <Dashboard onNavigate={(p, t) => navigate(p, t)}/>;
    }
  };

  return (
    <AdminShell page={page} tab={tab} year={year} month={month} onNavigate={(p) => set('page', p)}>
      {renderPage()}
    </AdminShell>
  );
}

export default App;

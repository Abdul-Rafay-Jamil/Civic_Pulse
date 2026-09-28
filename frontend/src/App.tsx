import { useState } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import { SubmitPage } from './pages/SubmitPage';
import { DashboardPage } from './pages/DashboardPage';
import { StatsPage } from './pages/StatsPage';

type View = 'submit' | 'dashboard' | 'stats';

function App() {
  const [view, setView] = useState<View>('submit');

  return (
    <ErrorBoundary>
      <div className="app-layout">
        <header className="app-header">
          <div className="header-content">
            <div className="logo">
              <div className="logo-icon">🏛</div>
              <span>CivicPulse</span>
            </div>
            <nav className="nav-tabs">
              <button
                className={`nav-tab ${view === 'submit' ? 'active' : ''}`}
                onClick={() => setView('submit')}
                id="nav-submit"
              >
                📝 Submit
              </button>
              <button
                className={`nav-tab ${view === 'dashboard' ? 'active' : ''}`}
                onClick={() => setView('dashboard')}
                id="nav-dashboard"
              >
                📋 Dashboard
              </button>
              <button
                className={`nav-tab ${view === 'stats' ? 'active' : ''}`}
                onClick={() => setView('stats')}
                id="nav-stats"
              >
                📊 Stats
              </button>
            </nav>
          </div>
        </header>

        <main className="app-main">
          {view === 'submit' && <SubmitPage />}
          {view === 'dashboard' && <DashboardPage />}
          {view === 'stats' && <StatsPage />}
        </main>
      </div>
    </ErrorBoundary>
  );
}

export default App;

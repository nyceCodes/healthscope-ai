import { lazy, Suspense } from "react";
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
} from "react-router-dom";
import "./App.css";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const PredictiveAnalytics = lazy(() => import("./pages/PredictiveAnalytics"));

function App() {
  return (
    <BrowserRouter>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <nav className="app-navigation" aria-label="Main navigation">
        <NavLink to="/" end>Dashboard</NavLink>
        <NavLink to="/predictive-analytics">Predictive analytics</NavLink>
      </nav>
      <main id="main-content" tabIndex={-1}>
        <Suspense fallback={<p className="route-loading" role="status">Loading page…</p>}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/predictive-analytics" element={<PredictiveAnalytics />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
    </BrowserRouter>
  );
}

export default App;

import { Suspense, lazy, useEffect, useRef } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { AssistantProvider } from "./context/AssistantContext";
import { SettingsProvider, useSettings } from "./context/SettingsContext";
import { SystemProvider } from "./context/SystemContext";
import { AppLayout } from "./layouts/AppLayout";
import AssistantPage from "./pages/AssistantPage";
import CapabilitiesPage from "./pages/CapabilitiesPage";
import DashboardPage from "./pages/DashboardPage";
import HistoryPage from "./pages/HistoryPage";
import SettingsPage from "./pages/SettingsPage";

// Recharts is only needed on the analytics page, so it is split into its own chunk.
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));

/** Honour the "start page" setting once, on first load. */
function StartPageRedirect() {
  const { settings, loaded } = useSettings();
  const navigate = useNavigate();
  const location = useLocation();
  const done = useRef(false);
  useEffect(() => {
    if (!loaded || done.current) return;
    done.current = true;
    if (location.pathname === "/" && settings.start_page === "assistant") navigate("/assistant", { replace: true });
  }, [loaded, settings.start_page, location.pathname, navigate]);
  return null;
}

export default function App() {
  return (
    <SettingsProvider>
      <SystemProvider>
        <AssistantProvider>
          <BrowserRouter>
            <StartPageRedirect />
            <Routes>
              <Route element={<AppLayout />}>
                <Route index element={<DashboardPage />} />
                <Route path="assistant" element={<AssistantPage />} />
                <Route path="history" element={<HistoryPage />} />
                <Route path="capabilities" element={<CapabilitiesPage />} />
                <Route path="analytics" element={<Suspense fallback={<div className="text-sm text-muted">Loading analytics…</div>}><AnalyticsPage /></Suspense>} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AssistantProvider>
      </SystemProvider>
    </SettingsProvider>
  );
}

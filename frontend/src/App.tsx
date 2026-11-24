import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AssistantProvider } from "./context/AssistantContext";
import { SettingsProvider } from "./context/SettingsContext";
import { SystemProvider } from "./context/SystemContext";
import { AppLayout } from "./layouts/AppLayout";
import HomePage from "./pages/HomePage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <SettingsProvider>
      <SystemProvider>
        <AssistantProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<AppLayout />}>
                <Route index element={<HomePage />} />
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

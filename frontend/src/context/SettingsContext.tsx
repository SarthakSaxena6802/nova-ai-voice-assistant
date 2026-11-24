import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../services/api";
import type { NovaSettings } from "../types/api";

export const DEFAULT_SETTINGS: NovaSettings = {
  assistant_name: "Nova",
  user_name: "",
  theme: "dark",
  voice_enabled: true,
  voice_name: "",
  speech_rate: 1,
  auto_send_voice: true,
  wake_word_enabled: true,
  execute_threshold: 0.75,
  clarify_threshold: 0.45,
  context_timeout_seconds: 120,
};

interface SettingsContextValue {
  settings: NovaSettings;
  loaded: boolean;
  error: string | null;
  update: (patch: Partial<NovaSettings>) => Promise<NovaSettings>;
  reload: () => Promise<void>;
  replace: (s: NovaSettings) => void;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

function applyTheme(theme: string) {
  document.documentElement.dataset.theme = theme;
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<NovaSettings>(() => {
    try {
      const cached = localStorage.getItem("nova-settings");
      return cached ? { ...DEFAULT_SETTINGS, ...JSON.parse(cached) } : DEFAULT_SETTINGS;
    } catch {
      return DEFAULT_SETTINGS;
    }
  });
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const replace = useCallback((s: NovaSettings) => {
    setSettings(s);
    try {
      localStorage.setItem("nova-settings", JSON.stringify(s));
    } catch {
      /* storage unavailable */
    }
  }, []);

  const reload = useCallback(async () => {
    try {
      replace(await api.settings());
      setError(null);
      setLoaded(true);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [replace]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => applyTheme(settings.theme), [settings.theme]);

  const update = useCallback(
    async (patch: Partial<NovaSettings>) => {
      const saved = await api.updateSettings(patch);
      replace(saved);
      return saved;
    },
    [replace],
  );

  return (
    <SettingsContext.Provider value={{ settings, loaded, error, update, reload, replace }}>{children}</SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings must be used inside SettingsProvider");
  return ctx;
}

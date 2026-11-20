import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { useInterval } from "../hooks/useTimers";
import { api } from "../services/api";
import type { Health } from "../types/api";

interface SystemContextValue {
  health: Health | null;
  online: boolean;
  checked: boolean;
  refresh: () => Promise<void>;
}

const SystemContext = createContext<SystemContextValue | null>(null);

export function SystemProvider({ children }: { children: ReactNode }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [online, setOnline] = useState(false);
  const [checked, setChecked] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setHealth(await api.health());
      setOnline(true);
    } catch {
      setOnline(false);
    } finally {
      setChecked(true);
    }
  }, []);

  useInterval(refresh, 10000);

  return <SystemContext.Provider value={{ health, online, checked, refresh }}>{children}</SystemContext.Provider>;
}

export function useSystem() {
  const ctx = useContext(SystemContext);
  if (!ctx) throw new Error("useSystem must be used inside SystemProvider");
  return ctx;
}

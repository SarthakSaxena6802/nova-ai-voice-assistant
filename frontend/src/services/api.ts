import type {
  Analytics,
  CapabilitiesResponse,
  FocusSession,
  FocusStatus,
  Health,
  HistoryPage,
  InputSource,
  ModelInfoResponse,
  NotificationItem,
  NovaSettings,
  PredictResponse,
  ProcessResult,
  Reminder,
  Timer,
} from "../types/api";

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function describe(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? String(d)).join("; ");
  return "Request failed";
}

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = 30000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    });
  } catch (err) {
    throw new ApiError(0, controller.signal.aborted ? "The request timed out." : "Can't reach the Nova backend. Is it running?");
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(res.status, describe(detail));
  }
  return (await res.json()) as T;
}

const json = (body: unknown) => JSON.stringify(body);

export const api = {
  health: () => request<Health>("/api/health", {}, 5000),
  process: (text: string, source: InputSource, session_id: string) =>
    request<ProcessResult>("/api/assistant/process", { method: "POST", body: json({ text, source, session_id }) }, 60000),
  resetContext: (session_id: string) =>
    request<{ ok: boolean }>("/api/assistant/reset-context", { method: "POST", body: json({ session_id }) }),
  capabilities: () => request<CapabilitiesResponse>("/api/assistant/capabilities"),

  timers: () => request<Timer[]>("/api/timers"),
  createTimer: (duration_seconds: number, label = "Timer") =>
    request<Timer>("/api/timers", { method: "POST", body: json({ duration_seconds, label }) }),
  cancelTimer: (id: number) => request<Timer>(`/api/timers/${id}`, { method: "DELETE" }),

  reminders: (status: "pending" | "completed" | "all" = "pending") => request<Reminder[]>(`/api/reminders?status=${status}`),
  createReminder: (message: string, due_at: string) =>
    request<Reminder>("/api/reminders", { method: "POST", body: json({ message, due_at }) }),
  completeReminder: (id: number) => request<Reminder>(`/api/reminders/${id}/complete`, { method: "PATCH" }),
  deleteReminder: (id: number) => request<{ ok: boolean }>(`/api/reminders/${id}`, { method: "DELETE" }),
  clearReminders: () => request<{ deleted: number }>("/api/reminders", { method: "DELETE" }),

  focus: () => request<FocusStatus>("/api/focus"),
  startFocus: (duration_minutes?: number) =>
    request<FocusSession>("/api/focus/start", { method: "POST", body: json({ duration_minutes: duration_minutes ?? null }) }),
  stopFocus: () => request<FocusSession>("/api/focus/stop", { method: "POST" }),

  notifications: () => request<NotificationItem[]>("/api/notifications", {}, 8000),
  markNotificationRead: (id: number) => request<{ updated: number }>(`/api/notifications/${id}/read`, { method: "POST" }),

  history: (params: { limit?: number; offset?: number; intent?: string; decision?: string; search?: string }) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && q.set(k, String(v)));
    return request<HistoryPage>(`/api/history?${q.toString()}`);
  },
  clearHistory: () => request<{ deleted: number }>("/api/history", { method: "DELETE" }),
  analytics: (days = 14) => request<Analytics>(`/api/analytics?days=${days}`),
  clearAnalytics: () => request<{ deleted: number }>("/api/analytics", { method: "DELETE" }),

  settings: () => request<NovaSettings>("/api/settings"),
  updateSettings: (patch: Partial<NovaSettings>) => request<NovaSettings>("/api/settings", { method: "PUT", body: json(patch) }),
  resetSettings: () => request<NovaSettings>("/api/settings/reset", { method: "POST" }),

  model: () => request<ModelInfoResponse>("/api/model"),
  predict: (text: string) => request<PredictResponse>("/api/model/predict", { method: "POST", body: json({ text }) }),
  reloadModel: () => request<{ ok: boolean }>("/api/model/reload", { method: "POST" }),
};

import type { Health, InputSource, NotificationItem, NovaSettings, ProcessResult, Reminder, Timer } from "../types/api";

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
  } catch {
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

  timers: () => request<Timer[]>("/api/timers"),
  cancelTimer: (id: number) => request<Timer>(`/api/timers/${id}`, { method: "DELETE" }),

  reminders: () => request<Reminder[]>("/api/reminders?status=pending"),
  completeReminder: (id: number) => request<Reminder>(`/api/reminders/${id}/complete`, { method: "PATCH" }),
  deleteReminder: (id: number) => request<{ ok: boolean }>(`/api/reminders/${id}`, { method: "DELETE" }),

  notifications: () => request<NotificationItem[]>("/api/notifications", {}, 8000),
  markNotificationRead: (id: number) => request<{ updated: number }>(`/api/notifications/${id}/read`, { method: "POST" }),

  settings: () => request<NovaSettings>("/api/settings"),
  updateSettings: (patch: Partial<NovaSettings>) => request<NovaSettings>("/api/settings", { method: "PUT", body: json(patch) }),
  resetSettings: () => request<NovaSettings>("/api/settings/reset", { method: "POST" }),
};

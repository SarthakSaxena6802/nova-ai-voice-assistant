export const INTENT_LABELS: Record<string, string> = {
  GREETING: "Greeting",
  GET_TIME: "Get time",
  GET_DATE: "Get date",
  CALCULATE: "Calculate",
  SET_TIMER: "Timer",
  CREATE_REMINDER: "Reminder",
  OPEN_WEBSITE: "Open website",
  ASK_QUESTION: "Question",
  UNKNOWN: "Unknown",
};

export const DECISION_META: Record<string, { label: string; tone: "good" | "warn" | "bad" | "info" | "muted"; help: string }> = {
  EXECUTE: { label: "Execute", tone: "good", help: "Confident and all parameters present – the action was run." },
  CONFIRM: { label: "Confirm", tone: "warn", help: "Medium confidence – Nova asked before acting." },
  CLARIFY: { label: "Clarify", tone: "info", help: "Intent understood but a required parameter was missing." },
  UNKNOWN: { label: "Unknown", tone: "bad", help: "Low confidence or out-of-scope request – nothing was executed." },
  CANCELLED: { label: "Cancelled", tone: "muted", help: "The user cancelled a pending request." },
};

export const intentLabel = (intent: string) => INTENT_LABELS[intent] ?? intent;

export const pct = (v: number | null | undefined, digits = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? "–" : `${(v * 100).toFixed(digits)}%`;

export function formatClock(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(sec).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

export function formatDuration(totalSeconds: number): string {
  const s = Math.round(totalSeconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const parts = [h && `${h}h`, m && `${m}m`, sec && !h && `${sec}s`].filter(Boolean);
  return parts.length ? parts.join(" ") : "0s";
}

/** Backend timestamps are naive local times (same machine), so Date parses them as local. */
export const parseLocal = (iso: string) => new Date(iso);

export function formatTime(iso: string): string {
  return parseLocal(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export function formatDateTime(iso: string): string {
  const d = parseLocal(iso);
  const today = new Date();
  const tomorrow = new Date();
  tomorrow.setDate(today.getDate() + 1);
  const time = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  if (d.toDateString() === today.toDateString()) return `Today, ${time}`;
  if (d.toDateString() === tomorrow.toDateString()) return `Tomorrow, ${time}`;
  return `${d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" })}, ${time}`;
}

export function greetingFor(date = new Date()): string {
  const h = date.getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export function formatEntityValue(value: unknown): string {
  if (value === null || value === undefined) return "–";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function sessionId(): string {
  const key = "nova-session-id";
  try {
    const existing = sessionStorage.getItem(key);
    if (existing) return existing;
    const id = `s${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36).slice(-4)}`;
    sessionStorage.setItem(key, id);
    return id;
  } catch {
    return "default";
  }
}

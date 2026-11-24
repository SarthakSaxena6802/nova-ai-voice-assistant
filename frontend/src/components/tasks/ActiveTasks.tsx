import { AlarmClock, Bell, Check, Trash2, X } from "lucide-react";
import { useState } from "react";
import { useAssistant } from "../../context/AssistantContext";
import { useNow } from "../../hooks/useTimers";
import { api } from "../../services/api";
import { formatClock, formatDateTime, formatDuration, parseLocal } from "../../utils/format";
import { Card } from "../ui/primitives";

function useAction() {
  const { refreshTasks, pushToast } = useAssistant();
  const [busy, setBusy] = useState(false);
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await refreshTasks();
    } catch (e) {
      pushToast({ title: "Action failed", message: (e as Error).message, kind: "system" });
    } finally {
      setBusy(false);
    }
  };
  return { busy, run };
}

const remaining = (endsAt: string, now: number) => Math.max(0, (parseLocal(endsAt).getTime() - now) / 1000);

export function TimersCard() {
  const { timers } = useAssistant();
  const now = useNow(1000);
  const { busy, run } = useAction();
  return (
    <Card title="Active timers" icon={AlarmClock} action={<span className="text-xs text-muted">{timers.length} running</span>}>
      {timers.length === 0 ? (
        <p className="text-sm text-muted">No timers running. Try “set a timer for 5 minutes”.</p>
      ) : (
        <ul className="space-y-2.5">
          {timers.map((t) => {
            const left = remaining(t.ends_at, now);
            const progress = 1 - left / t.duration_seconds;
            return (
              <li key={t.id} className="rounded-xl border border-line/70 bg-surface2/60 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-xl font-semibold tabular-nums tracking-tight">{formatClock(left)}</div>
                    <div className="truncate text-xs text-muted">
                      {t.label} · {formatDuration(t.duration_seconds)}
                    </div>
                  </div>
                  <button className="btn-ghost p-2" disabled={busy} onClick={() => run(() => api.cancelTimer(t.id))} title="Cancel timer" aria-label="Cancel timer">
                    <X size={16} />
                  </button>
                </div>
                <div className="mt-2 h-1 overflow-hidden rounded-full bg-surface3">
                  <div className="h-full rounded-full bg-accent transition-[width] duration-1000 ease-linear" style={{ width: `${Math.min(100, progress * 100)}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

export function RemindersCard({ limit = 5 }: { limit?: number }) {
  const { reminders } = useAssistant();
  const { busy, run } = useAction();
  return (
    <Card title="Pending reminders" icon={Bell} action={<span className="text-xs text-muted">{reminders.length} pending</span>}>
      {reminders.length === 0 ? (
        <p className="text-sm text-muted">Nothing pending. Try “remind me to call mom at 6 pm”.</p>
      ) : (
        <ul className="divide-y divide-line/60">
          {reminders.slice(0, limit).map((r) => (
            <li key={r.id} className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0">
              <div className={`h-2 w-2 shrink-0 rounded-full ${r.overdue ? "bg-warn" : "bg-accent"}`} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm text-ink first-letter:uppercase">{r.message}</div>
                <div className={`text-xs ${r.overdue ? "text-warn" : "text-muted"}`}>
                  {r.overdue ? "Due · " : ""}
                  {formatDateTime(r.due_at)}
                </div>
              </div>
              <button className="btn-ghost p-1.5" disabled={busy} onClick={() => run(() => api.completeReminder(r.id))} title="Mark as done" aria-label="Mark as done">
                <Check size={15} />
              </button>
              <button className="btn-ghost p-1.5" disabled={busy} onClick={() => run(() => api.deleteReminder(r.id))} title="Delete" aria-label="Delete reminder">
                <Trash2 size={15} />
              </button>
            </li>
          ))}
          {reminders.length > limit && <li className="pt-2 text-xs text-muted">+{reminders.length - limit} more</li>}
        </ul>
      )}
    </Card>
  );
}

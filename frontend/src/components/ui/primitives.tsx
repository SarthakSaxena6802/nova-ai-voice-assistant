import { useEffect, useState, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { DECISION_META, intentLabel, pct } from "../../utils/format";

export function Card({ children, className = "", title, action, icon: Icon }: {
  children: ReactNode;
  className?: string;
  title?: ReactNode;
  action?: ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 px-5 pt-4">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-ink">
            {Icon && <Icon size={16} className="text-muted" />}
            {title}
          </h2>
          {action}
        </header>
      )}
      <div className={title || action ? "px-5 pb-5 pt-3" : "p-5"}>{children}</div>
    </section>
  );
}

const TONES = {
  good: "border-good/30 bg-good/10 text-good",
  warn: "border-warn/30 bg-warn/10 text-warn",
  bad: "border-bad/30 bg-bad/10 text-bad",
  info: "border-info/30 bg-info/10 text-info",
  accent: "border-accent/30 bg-accent/10 text-accent",
  muted: "border-line bg-surface3 text-ink2",
} as const;
export type Tone = keyof typeof TONES;

export function Badge({ tone = "muted", children, className = "", title }: { tone?: Tone; children: ReactNode; className?: string; title?: string }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md border px-2 py-0.5 text-[11px] font-semibold tracking-wide ${TONES[tone]} ${className}`}>
      {children}
    </span>
  );
}

export function IntentBadge({ intent }: { intent: string }) {
  return (
    <Badge tone={intent === "UNKNOWN" ? "muted" : "accent"} className="font-mono" title={intentLabel(intent)}>
      {intent}
    </Badge>
  );
}

export function DecisionBadge({ decision }: { decision: string }) {
  const meta = DECISION_META[decision] ?? { label: decision, tone: "muted" as const, help: "" };
  return (
    <Badge tone={meta.tone} title={meta.help}>
      {meta.label.toUpperCase()}
    </Badge>
  );
}

/** Horizontal confidence bar with optional decision-threshold markers. */
export function ConfidenceBar({ value, thresholds, size = "md", tone }: {
  value: number;
  thresholds?: { execute: number; clarify: number };
  size?: "sm" | "md";
  tone?: "accent" | "muted";
}) {
  const color = tone === "muted"
    ? "bg-ink2/40"
    : thresholds
      ? value >= thresholds.execute ? "bg-good" : value >= thresholds.clarify ? "bg-warn" : "bg-bad"
      : "bg-accent";
  return (
    <div className={`relative w-full overflow-visible rounded-full bg-surface3 ${size === "sm" ? "h-1.5" : "h-2.5"}`}>
      <div className={`h-full rounded-full ${color} transition-[width] duration-500`} style={{ width: `${Math.max(1.5, value * 100)}%` }} />
      {thresholds && (
        <>
          <Marker at={thresholds.clarify} label={`Clarify ${pct(thresholds.clarify, 0)}`} />
          <Marker at={thresholds.execute} label={`Execute ${pct(thresholds.execute, 0)}`} />
        </>
      )}
    </div>
  );
}

function Marker({ at, label }: { at: number; label: string }) {
  return (
    <div className="group absolute -top-1 bottom-[-4px] w-px bg-ink/60" style={{ left: `${at * 100}%` }} title={label}>
      <span className="pointer-events-none absolute -top-5 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-surface3 px-1.5 py-0.5 text-[10px] text-ink2 group-hover:block">
        {label}
      </span>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      <div className="mb-1 grid h-11 w-11 place-items-center rounded-2xl border border-line bg-surface2 text-muted">
        <Icon size={20} />
      </div>
      <p className="text-sm font-medium text-ink">{title}</p>
      {children && <div className="max-w-sm text-sm text-muted">{children}</div>}
    </div>
  );
}

export function Toggle({ checked, onChange, label, disabled }: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 shrink-0 rounded-full border transition disabled:opacity-50 ${checked ? "border-accent bg-accent" : "border-line bg-surface3"}`}
    >
      <span className={`absolute top-0.5 h-[18px] w-[18px] rounded-full bg-white shadow transition-all ${checked ? "left-[22px]" : "left-0.5"}`} />
    </button>
  );
}

export function StatTile({ label, value, hint, icon: Icon }: { label: string; value: ReactNode; hint?: ReactNode; icon?: LucideIcon }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between text-xs font-medium text-muted">
        {label}
        {Icon && <Icon size={15} />}
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-ink">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}

/** Two-step destructive button: first click arms it, second click confirms. */
export function ConfirmButton({ onConfirm, children, confirmLabel = "Click again to confirm", className = "btn-danger" }: {
  onConfirm: () => void | Promise<void>;
  children: ReactNode;
  confirmLabel?: string;
  className?: string;
}) {
  const [armed, setArmed] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!armed) return;
    const t = window.setTimeout(() => setArmed(false), 4000);
    return () => window.clearTimeout(t);
  }, [armed]);
  return (
    <button
      type="button"
      className={className}
      disabled={busy}
      onClick={async () => {
        if (!armed) return setArmed(true);
        setBusy(true);
        try {
          await onConfirm();
        } finally {
          setBusy(false);
          setArmed(false);
        }
      }}
    >
      {armed ? confirmLabel : children}
    </button>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="text-sm font-medium text-ink">{label}</div>
        {hint && <div className="mt-0.5 text-xs text-muted">{hint}</div>}
      </div>
      <div className="shrink-0 sm:w-72 sm:max-w-[50%]">{children}</div>
    </div>
  );
}

import { AlertTriangle, ArrowRight, Brain, CheckCircle2, CircleSlash, GitBranch, MinusCircle, ScanSearch, XCircle } from "lucide-react";
import type { ReactNode } from "react";
import type { ProcessResult } from "../../types/api";
import { DECISION_META, formatEntityValue, intentLabel, pct } from "../../utils/format";
import { ConfidenceBar, DecisionBadge, EmptyState, IntentBadge } from "../ui/primitives";

function Section({ step, title, children, aside }: { step: number; title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="relative border-l border-line/80 pb-5 pl-5 last:border-transparent last:pb-0">
      <span className="absolute -left-[11px] top-0 grid h-[22px] w-[22px] place-items-center rounded-full border border-line bg-surface2 text-[10px] font-semibold text-ink2">
        {step}
      </span>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-[12px] font-semibold uppercase tracking-[0.08em] text-muted">{title}</h3>
        {aside}
      </div>
      {children}
    </div>
  );
}

const STEP_ICON = { ok: CheckCircle2, warn: AlertTriangle, error: XCircle, skip: MinusCircle } as const;
const STEP_TONE = { ok: "text-good", warn: "text-warn", error: "text-bad", skip: "text-muted" } as const;

export function DecisionInspector({ data, compact = false }: { data: ProcessResult | null; compact?: boolean }) {
  if (!data) {
    return (
      <EmptyState icon={ScanSearch} title="No decision to inspect yet">
        Send a command and Nova will show every step of its reasoning here — the classifier's probabilities, extracted
        entities, the confidence thresholds and the final decision.
      </EmptyState>
    );
  }
  const overridden = data.intent !== data.predicted_intent;
  const t = data.thresholds;
  const decisionMeta = DECISION_META[data.decision];

  return (
    <div className="pl-3">
      <Section step={1} title="Input">
        <div className="space-y-1.5 text-sm">
          <Row label={data.source === "voice" ? "Transcript" : "Original"}>
            <span className="text-ink">“{data.input}”</span>
            <span className="ml-2 text-[11px] text-muted">via {data.source.replace("_", " ")}</span>
          </Row>
          <Row label="Normalised">
            <code className="mono text-ink2">{data.normalized}</code>
          </Row>
          {data.model_input && (
            <Row label="Model input">
              <code className="mono text-ink2">{data.model_input}</code>
            </Row>
          )}
        </div>
      </Section>

      <Section step={2} title="Intent classification" aside={<span className="text-[11px] text-muted">TF-IDF + LogReg</span>}>
        <div className="mb-3 flex items-center gap-2">
          <IntentBadge intent={data.predicted_intent} />
          <span className="text-lg font-semibold tabular-nums">{pct(data.confidence)}</span>
          <span className="text-xs text-muted">confidence</span>
        </div>
        <ConfidenceBar value={data.confidence} thresholds={t} />
        {t && (
          <div className="mt-1.5 flex justify-between text-[11px] text-muted">
            <span>Clarify ≥ {pct(t.clarify, 0)}</span>
            <span>Execute ≥ {pct(t.execute, 0)}</span>
          </div>
        )}
        {data.top_intents.length > 0 && (
          <div className="mt-4 space-y-2">
            <div className="text-[11px] font-medium text-muted">Top predictions (softmax probabilities)</div>
            {data.top_intents.slice(0, 3).map((s, i) => (
              <div key={s.intent} className="grid grid-cols-[110px_1fr_52px] items-center gap-2 text-xs">
                <span className={`truncate font-mono ${i === 0 ? "text-ink" : "text-ink2"}`} title={intentLabel(s.intent)}>
                  {s.intent}
                </span>
                <ConfidenceBar value={s.confidence} size="sm" tone={i === 0 ? "accent" : "muted"} />
                <span className="text-right tabular-nums text-ink2">{pct(s.confidence)}</span>
              </div>
            ))}
          </div>
        )}
        {!compact && data.explanation.length > 0 && (
          <div className="mt-4">
            <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium text-muted">
              <Brain size={12} /> Features that pushed towards {data.predicted_intent} (tf-idf × coefficient)
            </div>
            <div className="flex flex-wrap gap-1.5">
              {data.explanation.map((f) => (
                <span key={`${f.kind}-${f.feature}`} className="chip font-mono text-[11px]" title={`${f.kind} n-gram, contribution ${f.weight}`}>
                  {f.kind === "char" ? `‹${f.feature}›` : f.feature}
                  <span className="text-accent">+{f.weight.toFixed(2)}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </Section>

      <Section step={3} title="Entities">
        {Object.keys(data.entities).length === 0 && data.missing_entities.length === 0 ? (
          <p className="text-sm text-muted">No parameters needed or extracted.</p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-line/70">
            <table className="w-full text-sm">
              <tbody>
                {Object.entries(data.entities).map(([k, v]) => (
                    <tr key={k} className="border-b border-line/60 last:border-0">
                      <td className="w-36 bg-surface2/60 px-3 py-1.5 font-mono text-xs text-muted">{k}</td>
                      <td className="px-3 py-1.5 text-ink">{formatEntityValue(v)}</td>
                    </tr>
                  ))}
                {data.missing_entities.map((k) => (
                  <tr key={`missing-${k}`} className="border-b border-line/60 last:border-0">
                    <td className="w-36 bg-surface2/60 px-3 py-1.5 font-mono text-xs text-muted">{k}</td>
                    <td className="px-3 py-1.5 text-warn">missing → ask the user</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data.notes.length > 0 && <ul className="mt-2 space-y-1 text-xs text-muted">{data.notes.map((n) => <li key={n}>• {n}</li>)}</ul>}
      </Section>

      <Section step={4} title="Decision">
        <div className="flex flex-wrap items-center gap-2">
          <DecisionBadge decision={data.decision} />
          {data.context_used && (
            <span className="chip text-[11px]">
              <GitBranch size={12} /> context: {data.context_used}
            </span>
          )}
          {overridden && (
            <span className="chip text-[11px]">
              {data.predicted_intent} <ArrowRight size={11} /> {data.intent}
            </span>
          )}
        </div>
        <p className="mt-2 text-sm leading-relaxed text-ink2">{data.decision_reason}</p>
        {decisionMeta && <p className="mt-1 text-xs text-muted">{decisionMeta.help}</p>}
      </Section>

      <Section step={5} title="Action & response">
        <div className="flex items-center gap-2 text-sm">
          {data.action ? (
            <>
              {data.success ? <CheckCircle2 size={16} className="text-good" /> : <XCircle size={16} className="text-bad" />}
              <span className="font-mono text-xs">{data.action}</span>
              <span className="text-muted">{data.success ? "executed successfully" : "did not succeed"}</span>
            </>
          ) : (
            <>
              <CircleSlash size={16} className="text-muted" />
              <span className="text-muted">No action executed</span>
            </>
          )}
        </div>
        <blockquote className="mt-2 rounded-xl border border-line/70 bg-surface2/60 px-3.5 py-2.5 text-sm text-ink">“{data.response}”</blockquote>
      </Section>

      {!compact && data.pipeline.length > 0 && (
        <Section step={6} title="Pipeline trace" aside={<span className="text-[11px] tabular-nums text-muted">{data.processing_ms.toFixed(1)} ms total</span>}>
          <ol className="space-y-1.5">
            {data.pipeline.map((s, i) => {
              const Icon = STEP_ICON[s.status] ?? CheckCircle2;
              return (
                <li key={i} className="grid grid-cols-[16px_1fr_auto] items-start gap-2 text-xs">
                  <Icon size={14} className={`mt-0.5 ${STEP_TONE[s.status]}`} />
                  <div>
                    <span className="font-medium text-ink">{s.title}</span>
                    <span className="text-ink2"> — {s.detail}</span>
                  </div>
                  <span className="tabular-nums text-muted">{s.ms !== null ? `${s.ms.toFixed(1)} ms` : ""}</span>
                </li>
              );
            })}
          </ol>
        </Section>
      )}
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[96px_1fr] gap-2">
      <span className="text-xs text-muted">{label}</span>
      <div className="min-w-0 break-words">{children}</div>
    </div>
  );
}

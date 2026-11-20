import { Activity, BarChart3, Brain, CheckCircle2, FlaskConical, Gauge, HelpCircle, MessagesSquare, RefreshCw, Timer, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { ChartTooltip, axisProps, useChartColors } from "../components/charts/chartTheme";
import { Card, ConfidenceBar, ConfirmButton, EmptyState, IntentBadge, StatTile } from "../components/ui/primitives";
import { api } from "../services/api";
import type { Analytics, ModelInfoResponse, PredictResponse } from "../types/api";
import { DECISION_META, intentLabel, pct } from "../utils/format";

export default function AnalyticsPage() {
  const [stats, setStats] = useState<Analytics | null>(null);
  const [model, setModel] = useState<ModelInfoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [a, m] = await Promise.all([api.analytics(14), api.model()]);
      setStats(a);
      setModel(m);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Usage analytics</h2>
          <p className="text-sm text-muted">Computed from your real interactions stored in SQLite (no raw text is kept in analytics).</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-outline px-3 py-1.5 text-xs" onClick={load}>
            <RefreshCw size={13} /> Refresh
          </button>
          <ConfirmButton className="btn-danger px-3 py-1.5 text-xs" confirmLabel="Delete analytics?" onConfirm={async () => { await api.clearAnalytics(); await load(); }}>
            <Trash2 size={13} /> Clear analytics
          </ConfirmButton>
        </div>
      </div>

      {error && <div className="rounded-xl border border-bad/30 bg-bad/10 px-4 py-3 text-sm">{error}</div>}

      {stats && stats.empty ? (
        <Card>
          <EmptyState icon={BarChart3} title="No usage data yet">
            Send a few commands to Nova and this page will show intent distribution, confidence scores and decision outcomes —
            all computed from real interactions.
          </EmptyState>
        </Card>
      ) : stats ? (
        <UsageSection stats={stats} />
      ) : null}

      <div className="pt-2">
        <h2 className="text-lg font-semibold">Model performance</h2>
        <p className="text-sm text-muted">Evaluation of the trained intent classifier on its held-out test split.</p>
      </div>
      {model?.report ? <ModelSection model={model} /> : model && (
        <Card><EmptyState icon={Brain} title="No training report found">Run <code className="mono">python ml/train_model.py</code> in the backend folder.</EmptyState></Card>
      )}
    </div>
  );
}

function UsageSection({ stats }: { stats: Analytics }) {
  const c = useChartColors();
  const daily = (stats.daily ?? []).map((d) => ({ ...d, label: new Date(d.date + "T00:00").toLocaleDateString([], { month: "short", day: "numeric" }) }));
  const intents = (stats.intent_distribution ?? []).map((d) => ({ ...d, name: d.intent }));
  const decisions = (stats.decision_distribution ?? []).map((d) => ({ ...d, name: DECISION_META[d.decision]?.label ?? d.decision }));

  return (
    <>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <StatTile label="Commands processed" value={stats.total} icon={MessagesSquare} hint={`${pct(stats.voice_share, 0)} by voice`} />
        <StatTile label="Executed" value={stats.executed} icon={CheckCircle2} hint={`${pct(stats.execution_rate, 0)} of commands`} />
        <StatTile label="Success rate" value={pct(stats.success_rate, 0)} icon={Gauge} hint={`${stats.successful} ok · ${stats.failed_actions} failed`} />
        <StatTile label="Needed clarification" value={stats.clarifications} icon={HelpCircle} hint={`${stats.confirmations} confirm · ${stats.missing_info} missing info`} />
        <StatTile label="Unknown" value={stats.unknown} icon={Activity} hint={`${stats.context_resolved} resolved via context`} />
        <StatTile label="Avg. confidence" value={pct(stats.avg_confidence, 1)} icon={Timer} hint={`${stats.avg_processing_ms} ms avg. pipeline`} />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Activity — last 14 days">
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={daily} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
                <CartesianGrid stroke={c.grid} vertical={false} />
                <XAxis dataKey="label" {...axisProps(c)} interval="preserveStartEnd" minTickGap={18} />
                <YAxis {...axisProps(c)} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ stroke: c.axis, strokeDasharray: "3 3" }} />
                <Legend iconType="plainline" wrapperStyle={{ fontSize: 12, color: c.axis }} />
                <Line type="linear" dataKey="total" name="All commands" stroke={c.series1} strokeWidth={2} dot={false} activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2 }} />
                <Line type="linear" dataKey="executed" name="Executed" stroke={c.series2} strokeWidth={2} dot={false} activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Intent distribution">
          <div style={{ height: Math.max(180, intents.length * 30 + 20) }}>
            <ResponsiveContainer>
              <BarChart data={intents} layout="vertical" margin={{ top: 0, right: 24, left: 8, bottom: 0 }} barCategoryGap={6}>
                <CartesianGrid stroke={c.grid} horizontal={false} />
                <XAxis type="number" {...axisProps(c)} allowDecimals={false} />
                <YAxis type="category" dataKey="name" {...axisProps(c)} width={128} tickFormatter={(v: string) => v} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: c.grid }} />
                <Bar dataKey="count" name="Commands" fill={c.series1} radius={[0, 4, 4, 0]} maxBarSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Confidence distribution">
          <p className="-mt-1 mb-3 text-xs text-muted">How sure the classifier was about each command (top-intent probability).</p>
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={stats.confidence_histogram} margin={{ top: 4, right: 8, left: -18, bottom: 0 }} barCategoryGap={2}>
                <CartesianGrid stroke={c.grid} vertical={false} />
                <XAxis dataKey="bucket" {...axisProps(c)} interval={1} />
                <YAxis {...axisProps(c)} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: c.grid }} />
                <Bar dataKey="count" name="Commands" fill={c.series1} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Decision outcomes">
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={decisions} layout="vertical" margin={{ top: 0, right: 24, left: 8, bottom: 0 }} barCategoryGap={8}>
                <CartesianGrid stroke={c.grid} horizontal={false} />
                <XAxis type="number" {...axisProps(c)} allowDecimals={false} />
                <YAxis type="category" dataKey="name" {...axisProps(c)} width={84} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: c.grid }} />
                <Bar dataKey="count" name="Commands" fill={c.series1} radius={[0, 4, 4, 0]} maxBarSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 overflow-hidden rounded-xl border border-line/70">
            <table className="w-full text-xs">
              <thead className="bg-surface2/70 text-muted">
                <tr>
                  <th className="px-3 py-1.5 text-left font-medium">Intent</th>
                  <th className="px-3 py-1.5 text-right font-medium">Commands</th>
                  <th className="px-3 py-1.5 text-right font-medium">Avg. confidence</th>
                </tr>
              </thead>
              <tbody>
                {(stats.confidence_by_intent ?? []).map((r) => (
                  <tr key={r.intent} className="border-t border-line/60">
                    <td className="px-3 py-1.5 font-mono">{r.intent}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{r.count}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{pct(r.avg_confidence)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </>
  );
}

function ModelSection({ model }: { model: ModelInfoResponse }) {
  const r = model.report!;
  const c = useChartColors();
  const perClass = Object.entries(r.test_metrics.per_class).map(([intent, m]) => ({ name: intent, f1: m.f1, precision: m.precision, recall: m.recall, support: m.support }));
  const { labels, matrix } = r.test_metrics.confusion_matrix;
  const max = Math.max(1, ...matrix.flat());

  return (
    <>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <StatTile label="Test accuracy" value={pct(r.metrics.accuracy)} hint={`${r.test_size} held-out sentences`} />
        <StatTile label="Macro F1" value={pct(r.metrics.f1_macro)} hint={`P ${pct(r.metrics.precision_macro, 0)} · R ${pct(r.metrics.recall_macro, 0)}`} />
        <StatTile label="5-fold CV accuracy" value={pct(r.metrics.cv_accuracy_mean)} hint={`± ${pct(r.metrics.cv_accuracy_std)}`} />
        <StatTile label="Unseen phrasings" value={pct(r.metrics.unseen_accuracy)} hint={`${r.unseen_evaluation?.size ?? 0} novel sentences`} />
        <StatTile label="Dataset" value={r.dataset_size} hint={`${labels.length} intents · train ${r.train_size}`} />
        <StatTile label="Regularisation C" value={r.hyperparameters.C} hint={`chosen by grid search (CV F1 ${pct(r.hyperparameters.cv_best_macro_f1, 1)})`} />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Confusion matrix (test split)">
          <p className="-mt-1 mb-3 text-xs text-muted">Rows are the true intent, columns the predicted one. The diagonal counts correct predictions.</p>
          <div className="overflow-x-auto">
            <table className="border-separate border-spacing-[2px] text-[11px]">
              <thead>
                <tr>
                  <th />
                  {labels.map((l) => (
                    <th key={l} className="h-24 w-8 align-bottom font-normal text-muted">
                      <div className="mx-auto w-4 origin-bottom-left translate-x-3 -rotate-90 whitespace-nowrap text-left font-mono">{l}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.map((row, i) => (
                  <tr key={labels[i]}>
                    <th className="whitespace-nowrap pr-2 text-right font-mono font-normal text-muted">{labels[i]}</th>
                    {row.map((v, j) => {
                      const level = v === 0 ? 0 : Math.min(4, 1 + Math.floor((v / max) * 3.999));
                      const bg = c.heat[level];
                      return (
                        <td
                          key={j}
                          title={`True ${labels[i]} → predicted ${labels[j]}: ${v}`}
                          className={`h-8 w-8 rounded text-center tabular-nums ${i === j ? "font-semibold" : ""}`}
                          style={{ background: bg, color: v === 0 ? "transparent" : isLight(bg) ? "#0b0b0b" : "#ffffff" }}
                        >
                          {v}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Per-intent F1 score">
          <div style={{ height: perClass.length * 28 + 30 }}>
            <ResponsiveContainer>
              <BarChart data={perClass} layout="vertical" margin={{ top: 0, right: 24, left: 8, bottom: 0 }} barCategoryGap={5}>
                <CartesianGrid stroke={c.grid} horizontal={false} />
                <XAxis type="number" domain={[0, 1]} {...axisProps(c)} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
                <YAxis type="category" dataKey="name" {...axisProps(c)} width={128} />
                <Tooltip content={<ChartTooltip format={(v) => pct(v)} />} cursor={{ fill: c.grid }} />
                <Bar dataKey="f1" name="F1" fill={c.series1} radius={[0, 4, 4, 0]} maxBarSize={16}>
                  {perClass.map((p) => <Cell key={p.name} fill={c.series1} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          {r.misclassified_test_examples.length > 0 && (
            <details className="mt-3 text-xs">
              <summary className="cursor-pointer text-ink2">{r.misclassified_test_examples.length} misclassified test sentences</summary>
              <ul className="mt-2 space-y-1 text-muted">
                {r.misclassified_test_examples.map((m) => (
                  <li key={m.text}>
                    “{m.text}” — expected <span className="font-mono text-ink2">{m.expected}</span>, predicted{" "}
                    <span className="font-mono text-ink2">{m.predicted}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </Card>
      </div>

      <Playground />
    </>
  );
}

/** Relative luminance check so heatmap labels stay readable on every ramp step. */
function isLight(hex: string): boolean {
  const m = hex.replace("#", "").match(/.{2}/g);
  if (!m) return false;
  const [r, g, b] = m.map((x) => parseInt(x, 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.35;
}

function Playground() {
  const [text, setText] = useState("could you start a countdown for five minutes");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const submit = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!text.trim()) return;
    try {
      setResult(await api.predict(text));
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };
  return (
    <Card title="Classifier playground" icon={FlaskConical}>
      <p className="-mt-1 mb-3 text-xs text-muted">Runs only the ML model — nothing is executed or stored.</p>
      <form onSubmit={submit} className="flex gap-2">
        <input className="input" value={text} onChange={(e) => setText(e.target.value)} maxLength={500} placeholder="Type any sentence…" />
        <button className="btn-primary" type="submit">Classify</button>
      </form>
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}
      {result && (
        <div className="mt-4 grid gap-5 lg:grid-cols-2">
          <div className="space-y-2">
            <div className="mb-2 flex items-center gap-2 text-sm">
              <IntentBadge intent={result.intent} /> <span className="font-semibold tabular-nums">{pct(result.confidence)}</span>
              <span className="text-xs text-muted">· {result.inference_ms} ms · input “{result.model_input}”</span>
            </div>
            {result.ranking.map((s, i) => (
              <div key={s.intent} className="grid grid-cols-[130px_1fr_56px] items-center gap-2 text-xs">
                <span className="truncate font-mono text-ink2" title={intentLabel(s.intent)}>{s.intent}</span>
                <ConfidenceBar value={s.confidence} size="sm" tone={i === 0 ? "accent" : "muted"} />
                <span className="text-right tabular-nums text-ink2">{pct(s.confidence)}</span>
              </div>
            ))}
          </div>
          <div>
            <div className="mb-2 text-xs font-medium text-muted">Top contributing features</div>
            <div className="flex flex-wrap gap-1.5">
              {result.explanation.length ? result.explanation.map((f) => (
                <span key={`${f.kind}-${f.feature}`} className="chip font-mono text-[11px]">
                  {f.kind === "char" ? `‹${f.feature}›` : f.feature} <span className="text-accent">+{f.weight.toFixed(2)}</span>
                </span>
              )) : <span className="text-xs text-muted">No positive features.</span>}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

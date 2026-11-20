import { ChevronDown, History as HistoryIcon, Mic, Search, Trash2, Type, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { DecisionInspector, fromHistory } from "../components/inspector/DecisionInspector";
import { Card, ConfirmButton, DecisionBadge, EmptyState, IntentBadge } from "../components/ui/primitives";
import { api } from "../services/api";
import type { HistoryItem } from "../types/api";
import { DECISION_META, INTENT_LABELS, formatDateTime, pct } from "../utils/format";

const PAGE = 25;
const SOURCE_ICON = { voice: Mic, text: Type, quick_action: Zap } as const;

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [intent, setIntent] = useState("");
  const [decision, setDecision] = useState("");

  const load = useCallback(
    async (offset = 0) => {
      setLoading(true);
      try {
        const page = await api.history({ limit: PAGE, offset, intent, decision, search: search.trim() });
        setItems((prev) => (offset ? [...prev, ...page.items] : page.items));
        setTotal(page.total);
        setError(null);
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [intent, decision, search],
  );

  useEffect(() => {
    const t = window.setTimeout(() => load(0), 250);
    return () => window.clearTimeout(t);
  }, [load]);

  return (
    <Card
      title="Conversation history"
      icon={HistoryIcon}
      action={
        <ConfirmButton
          className="btn-danger px-3 py-1.5 text-xs"
          confirmLabel="Delete all history?"
          onConfirm={async () => {
            await api.clearHistory();
            setOpen(null);
            await load(0);
          }}
        >
          <Trash2 size={14} /> Clear history
        </ConfirmButton>
      }
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input className="input pl-9" placeholder="Search inputs and responses…" value={search} onChange={(e) => setSearch(e.target.value)} maxLength={100} />
        </div>
        <select className="input w-auto" value={intent} onChange={(e) => setIntent(e.target.value)} aria-label="Filter by intent">
          <option value="">All intents</option>
          {Object.keys(INTENT_LABELS).map((i) => (
            <option key={i} value={i}>
              {i}
            </option>
          ))}
        </select>
        <select className="input w-auto" value={decision} onChange={(e) => setDecision(e.target.value)} aria-label="Filter by decision">
          <option value="">All decisions</option>
          {Object.entries(DECISION_META).map(([k, v]) => (
            <option key={k} value={k}>
              {v.label}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="mb-3 rounded-xl border border-bad/30 bg-bad/10 px-4 py-3 text-sm">{error}</div>}

      {!loading && items.length === 0 && !error ? (
        <EmptyState icon={HistoryIcon} title={search || intent || decision ? "No matching interactions" : "No history yet"}>
          Every command you send is stored locally in SQLite with its prediction, confidence and decision.
        </EmptyState>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line/70">
          <div className="hidden grid-cols-[150px_minmax(0,1.3fr)_minmax(0,1.7fr)_150px_70px_100px_24px] gap-3 border-b border-line/70 bg-surface2/70 px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted lg:grid">
            <span>Time</span>
            <span>Input</span>
            <span>Response</span>
            <span>Intent</span>
            <span className="text-right">Conf.</span>
            <span>Decision</span>
            <span />
          </div>
          {items.map((h) => {
            const SourceIcon = SOURCE_ICON[h.source] ?? Type;
            const isOpen = open === h.id;
            return (
              <div key={h.id} className="border-b border-line/60 last:border-0">
                <button
                  type="button"
                  onClick={() => setOpen(isOpen ? null : h.id)}
                  className="grid w-full grid-cols-1 gap-1.5 px-4 py-3 text-left text-sm transition hover:bg-surface2/60 lg:grid-cols-[150px_minmax(0,1.3fr)_minmax(0,1.7fr)_150px_70px_100px_24px] lg:items-center lg:gap-3"
                >
                  <span className="flex items-center gap-1.5 text-xs text-muted">
                    <SourceIcon size={12} /> {formatDateTime(h.created_at)}
                  </span>
                  <span className="truncate text-ink">{h.raw_input}</span>
                  <span className="truncate text-ink2">{h.response}</span>
                  <span>
                    <IntentBadge intent={h.intent} />
                  </span>
                  <span className="tabular-nums text-ink2 lg:text-right">{pct(h.confidence)}</span>
                  <span>
                    <DecisionBadge decision={h.decision} />
                  </span>
                  <ChevronDown size={15} className={`hidden text-muted transition lg:block ${isOpen ? "rotate-180" : ""}`} />
                </button>
                {isOpen && (
                  <div className="animate-fade-in border-t border-line/60 bg-surface2/30 px-4 py-5 sm:px-8">
                    <DecisionInspector data={fromHistory(h)} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-4 flex items-center justify-between text-xs text-muted">
        <span>
          Showing {items.length} of {total}
        </span>
        {items.length < total && (
          <button className="btn-outline px-3 py-1.5 text-xs" disabled={loading} onClick={() => load(items.length)}>
            Load more
          </button>
        )}
      </div>
    </Card>
  );
}

import { AlertTriangle, ExternalLink, Info, Mic, Zap } from "lucide-react";
import { useEffect, useRef } from "react";
import { useAssistant, type ChatMessage } from "../../context/AssistantContext";
import { formatTime, pct } from "../../utils/format";
import { DecisionBadge, IntentBadge } from "../ui/primitives";

function NovaBubble({ m }: { m: ChatMessage }) {
  const { selected, selectResult } = useAssistant();
  const r = m.result!;
  const isSelected = selected === r;
  return (
    <button
      type="button"
      onClick={() => selectResult(r)}
      className={`group max-w-[85%] rounded-2xl rounded-tl-md border px-4 py-3 text-left transition ${
        isSelected ? "border-accent/50 bg-surface2" : "border-line/70 bg-surface2/70 hover:border-line"
      }`}
      title="Inspect this decision"
    >
      <p className="whitespace-pre-wrap text-[14.5px] leading-relaxed text-ink">{m.text}</p>
      {r.data?.url && (
        <a
          href={r.data.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="mt-2 inline-flex items-center gap-1 text-sm text-accent hover:underline"
        >
          {r.data.website ?? r.data.url} <ExternalLink size={13} />
        </a>
      )}
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        <IntentBadge intent={r.intent} />
        <DecisionBadge decision={r.decision} />
        <span className="text-[11px] text-muted">
          {pct(r.confidence)} · {Math.round(r.processing_ms)} ms
          {r.context_used && <> · context: {r.context_used}</>}
        </span>
      </div>
    </button>
  );
}

export function MessageList({ limit, className = "" }: { limit?: number; className?: string }) {
  const { messages, busy } = useAssistant();
  const end = useRef<HTMLDivElement>(null);
  const shown = limit ? messages.slice(-limit) : messages;

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages.length, busy]);

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      {shown.map((m) => (
        <div key={m.id} className={`flex animate-fade-in ${m.role === "user" ? "justify-end" : "justify-start"}`}>
          {m.role === "user" && (
            <div className="max-w-[80%] rounded-2xl rounded-tr-md bg-accent px-4 py-2.5 text-[14.5px] text-white shadow-sm">
              {m.text}
              <div className="mt-1 flex items-center justify-end gap-1 text-[11px] text-white/70">
                {m.source === "voice" && <Mic size={11} />}
                {m.source === "quick_action" && <Zap size={11} />}
                {formatTime(m.time)}
              </div>
            </div>
          )}
          {m.role === "nova" && m.result && <NovaBubble m={m} />}
          {m.role === "system" && (
            <div
              className={`flex max-w-[90%] items-start gap-2 rounded-xl border px-3.5 py-2.5 text-sm ${
                m.tone === "error" ? "border-bad/30 bg-bad/10 text-ink" : "border-line/70 bg-surface2/50 text-ink2"
              }`}
            >
              {m.tone === "error" ? <AlertTriangle size={15} className="mt-0.5 shrink-0 text-bad" /> : <Info size={15} className="mt-0.5 shrink-0 text-info" />}
              <span>{m.text}</span>
            </div>
          )}
        </div>
      ))}
      {busy && (
        <div className="flex justify-start">
          <div className="flex gap-1 rounded-2xl rounded-tl-md border border-line/70 bg-surface2/70 px-4 py-3.5">
            {[0, 1, 2].map((i) => (
              <span key={i} className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink2" style={{ animationDelay: `${i * 150}ms` }} />
            ))}
          </div>
        </div>
      )}
      <div ref={end} />
    </div>
  );
}

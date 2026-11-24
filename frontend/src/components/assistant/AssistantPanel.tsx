import { Mic, Send, Square, Trash2, VolumeX } from "lucide-react";
import { useEffect, useRef, type FormEvent } from "react";
import { useAssistant } from "../../context/AssistantContext";
import { useSettings } from "../../context/SettingsContext";
import { useSystem } from "../../context/SystemContext";
import { NovaOrb } from "./NovaOrb";

/** Orb + live transcript + text input + mic/send/clear controls. */
export function AssistantComposer({ autoFocus = false }: { autoFocus?: boolean }) {
  const { send, busy, recognition, wake, toggleListening, synthesis, clear, messages, draft, setDraft } = useAssistant();
  const listening = recognition.listening || wake.state === "awake";
  const transcript = recognition.transcript || wake.heard;
  const micError = recognition.error ?? wake.error;
  const { online } = useSystem();
  const { settings } = useSettings();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  // A transcript that wasn't auto-sent lands in the input for review.
  useEffect(() => {
    if (draft) inputRef.current?.focus();
  }, [draft]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!draft.trim()) return;
    send(draft, "text");
    setDraft("");
  };

  return (
    <div className="flex flex-col gap-3">
      {(listening || transcript) && (
        <div className="rounded-xl border border-accent/30 bg-accent/5 px-4 py-2.5 text-sm">
          <span className="mr-2 text-[11px] font-semibold uppercase tracking-wider text-accent">
            {listening ? "Hearing" : "Heard"}
          </span>
          <span className="text-ink">{transcript || "…"}</span>
        </div>
      )}
      {micError && (
        <div className="rounded-xl border border-warn/30 bg-warn/10 px-4 py-2.5 text-sm text-ink">{micError}</div>
      )}
      <form onSubmit={submit} className="flex items-center gap-2">
        <button
          type="button"
          onClick={toggleListening}
          disabled={!recognition.supported || busy || !online}
          title={
            !recognition.supported
              ? "Voice input isn't supported in this browser (use Chrome or Edge)"
              : wake.state !== "off"
                ? "Wake Nova (or just say \"Nova\")"
                : recognition.listening
                  ? "Stop listening"
                  : "Speak to Nova"
          }
          aria-label={listening ? "Stop listening" : "Start listening"}
          className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl border transition disabled:cursor-not-allowed disabled:opacity-40 ${
            listening
              ? "border-bad/50 bg-bad/15 text-bad"
              : "border-accent/40 bg-accent/10 text-accent hover:bg-accent/20"
          }`}
        >
          {recognition.listening ? <Square size={16} fill="currentColor" /> : <Mic size={18} />}
        </button>
        <input
          ref={inputRef}
          className="input h-11"
          placeholder={online ? `Ask ${settings.assistant_name} something…` : "Backend offline"}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          maxLength={500}
          disabled={!online}
          aria-label="Message"
        />
        <button type="submit" className="btn-primary h-11 w-11 shrink-0 p-0" disabled={!draft.trim() || busy || !online} aria-label="Send">
          <Send size={17} />
        </button>
      </form>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
        <span>
          {wake.state !== "off"
            ? 'Say "Nova" followed by a command, or type and press Enter.'
            : recognition.supported
            ? "Click the mic and speak, or type and press Enter."
            : "Voice input needs Chrome or Edge — typing works everywhere."}
        </span>
        <div className="flex items-center gap-1">
          {synthesis.speaking && (
            <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={synthesis.cancel}>
              <VolumeX size={14} /> Stop speaking
            </button>
          )}
          <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={clear} disabled={!messages.length}>
            <Trash2 size={14} /> Clear conversation
          </button>
        </div>
      </div>
    </div>
  );
}

export function AssistantHero() {
  const { status } = useAssistant();
  return (
    <div className="flex justify-center py-2">
      <NovaOrb status={status} />
    </div>
  );
}

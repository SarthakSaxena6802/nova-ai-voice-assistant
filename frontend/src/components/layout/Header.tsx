import { Brain, Mic, MicOff, Server, Volume2, VolumeX } from "lucide-react";
import type { ReactNode } from "react";
import { useAssistant } from "../../context/AssistantContext";
import { useSettings } from "../../context/SettingsContext";
import { useSystem } from "../../context/SystemContext";
import { useNow } from "../../hooks/useTimers";
import { greetingFor } from "../../utils/format";

function Pill({ ok, warn, icon, children, title }: { ok: boolean; warn?: boolean; icon: ReactNode; children: ReactNode; title?: string }) {
  const dot = ok ? "bg-good" : warn ? "bg-warn" : "bg-bad";
  return (
    <span title={title} className="chip whitespace-nowrap">
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {icon}
      {children}
    </span>
  );
}

const STATE_LABEL = { idle: "Idle", listening: "Listening", processing: "Thinking", speaking: "Speaking" } as const;

export function Header() {
  const now = useNow(30000);
  const { settings } = useSettings();
  const { online, health, checked } = useSystem();
  const { recognition, synthesis, status } = useAssistant();
  const name = settings.user_name ? `, ${settings.user_name}` : "";
  const date = new Date(now).toLocaleDateString([], { weekday: "long", month: "long", day: "numeric", year: "numeric" });

  return (
    <header className="flex flex-wrap items-end justify-between gap-4 pb-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {greetingFor(new Date(now))}
          {name}
        </h1>
        <p className="mt-1 text-sm text-muted">{date}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Pill
          ok={online && health?.status === "ok"}
          warn={online && health?.status !== "ok"}
          icon={<Server size={12} />}
          title={online ? "Backend connected" : "Backend not reachable – start it with uvicorn"}
        >
          {!checked ? "Connecting…" : online ? "Backend online" : "Backend offline"}
        </Pill>
        <Pill ok={!!health?.model.loaded} icon={<Brain size={12} />} title={health?.model.error ?? "Intent classifier status"}>
          {health?.model.loaded ? "Model loaded" : "Model unavailable"}
        </Pill>
        <Pill
          ok={recognition.supported}
          warn={!recognition.supported}
          icon={recognition.supported ? <Mic size={12} /> : <MicOff size={12} />}
          title={recognition.supported ? "Speech recognition available" : "Speech recognition not supported – use Chrome or Edge"}
        >
          {settings.wake_word_enabled && recognition.supported ? 'Say "Nova"' : recognition.supported ? "Mic ready" : "No speech input"}
        </Pill>
        <Pill
          ok={synthesis.supported && settings.voice_enabled}
          warn
          icon={settings.voice_enabled ? <Volume2 size={12} /> : <VolumeX size={12} />}
          title="Spoken responses"
        >
          {settings.voice_enabled ? "Voice on" : "Voice off"}
        </Pill>
        <span className="chip">
          <span className={`h-1.5 w-1.5 rounded-full ${status === "idle" ? "bg-muted" : "animate-pulse bg-accent"}`} />
          {STATE_LABEL[status]}
        </span>
      </div>
    </header>
  );
}

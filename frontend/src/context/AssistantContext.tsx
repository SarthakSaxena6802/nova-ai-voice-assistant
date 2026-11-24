import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useSpeechRecognition, type SpeechRecognitionState } from "../hooks/useSpeechRecognition";
import { useSpeechSynthesis, type SpeechSynthesisState } from "../hooks/useSpeechSynthesis";
import { useWakeWord, type WakeWordState } from "../hooks/useWakeWord";
import { useInterval } from "../hooks/useTimers";
import { api } from "../services/api";
import type { InputSource, ProcessResult, Reminder, Timer } from "../types/api";
import { greetingFor, sessionId } from "../utils/format";
import { playChime } from "../utils/sound";
import { useSettings } from "./SettingsContext";
import { useSystem } from "./SystemContext";

export type AssistantStatus = "idle" | "listening" | "processing" | "speaking";

export interface ChatMessage {
  id: string;
  role: "user" | "nova" | "system";
  text: string;
  time: string;
  source?: InputSource;
  result?: ProcessResult;
  tone?: "error" | "info";
}

export interface Toast {
  id: number;
  title: string;
  message: string;
  kind: string;
}

interface AssistantContextValue {
  sessionId: string;
  messages: ChatMessage[];
  status: AssistantStatus;
  busy: boolean;
  selected: ProcessResult | null;
  selectResult: (r: ProcessResult | null) => void;
  send: (text: string, source?: InputSource) => Promise<void>;
  clear: () => Promise<void>;
  recognition: SpeechRecognitionState;
  synthesis: SpeechSynthesisState;
  wake: WakeWordState;
  toggleListening: () => void;
  timers: Timer[];
  reminders: Reminder[];
  refreshTasks: () => Promise<void>;
  draft: string;
  setDraft: (v: string) => void;
  toasts: Toast[];
  dismissToast: (id: number) => void;
  pushToast: (t: Omit<Toast, "id">) => void;
}

const AssistantContext = createContext<AssistantContextValue | null>(null);
const uid = () => Math.random().toString(36).slice(2, 10);
const nowIso = () => new Date().toISOString();

export function AssistantProvider({ children }: { children: ReactNode }) {
  const { settings, loaded } = useSettings();
  const { online } = useSystem();
  const session = useMemo(() => sessionId(), []);
  // The conversation survives page reloads within this browser tab (sessionStorage).
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      return JSON.parse(sessionStorage.getItem("nova-messages") ?? "[]") as ChatMessage[];
    } catch {
      return [];
    }
  });
  useEffect(() => {
    try {
      sessionStorage.setItem("nova-messages", JSON.stringify(messages.slice(-60)));
    } catch {
      /* storage full or unavailable */
    }
  }, [messages]);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<ProcessResult | null>(null);
  const [timers, setTimers] = useState<Timer[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [draft, setDraft] = useState("");
  const greeted = useRef(false);

  const synthesis = useSpeechSynthesis({
    enabled: settings.voice_enabled,
    voiceName: settings.voice_name,
    rate: settings.speech_rate,
  });

  const pushToast = useCallback((t: Omit<Toast, "id">) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev.slice(-3), { ...t, id }]);
    window.setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 9000);
  }, []);
  const dismissToast = useCallback((id: number) => setToasts((prev) => prev.filter((x) => x.id !== id)), []);

  const refreshTasks = useCallback(async () => {
    try {
      const [t, r] = await Promise.all([api.timers(), api.reminders()]);
      setTimers(t);
      setReminders(r);
    } catch {
      /* backend offline – status pill shows it */
    }
  }, []);

  // ---------------------------------------------------------------- send a command
  const send = useCallback(
    async (raw: string, source: InputSource = "text") => {
      const text = raw.trim();
      if (!text || busy) return;
      synthesis.cancel();
      setMessages((prev) => [...prev, { id: uid(), role: "user", text, time: nowIso(), source }]);
      setBusy(true);
      try {
        const result = await api.process(text, source, session);
        const id = uid();
        setMessages((prev) => [...prev, { id, role: "nova", text: result.response, time: nowIso(), result }]);
        setSelected(result);
        synthesis.speak(result.response, `msg-${id}`);
        if (result.success && result.data?.url && result.data?.opened_by === "client") {
          // No "noopener" feature here: it makes window.open return null, and we need the handle to detect a blocked pop-up.
          const tab = window.open(result.data.url as string, "_blank");
          if (tab) tab.opener = null;
          else
            pushToast({
              title: "Pop-up blocked",
              message: `Click the ${result.data.website} link in Nova's reply, or allow pop-ups for this site so voice commands can open websites.`,
              kind: "system",
            });
        }
        if (["SET_TIMER", "CREATE_REMINDER"].includes(result.intent)) refreshTasks();
      } catch (e) {
        setMessages((prev) => [
          ...prev,
          { id: uid(), role: "system", text: (e as Error).message, time: nowIso(), tone: "error" },
        ]);
      } finally {
        setBusy(false);
      }
    },
    [busy, session, synthesis, refreshTasks, pushToast],
  );

  const recognition = useSpeechRecognition((finalText) => {
    if (settings.auto_send_voice) send(finalText, "voice");
    else setDraft(finalText);
  });

  // Hands-free: say "Nova …". The mic is closed while Nova is thinking or speaking, then reopened.
  const wake = useWakeWord(
    settings.wake_word_enabled && online && !recognition.listening && !busy && !synthesis.speaking,
    (cmd) => send(cmd, "voice"),
  );

  const toggleListening = useCallback(() => {
    if (wake.state !== "off") {
      synthesis.cancel();
      wake.wakeNow(); // one recognizer at a time: the mic button just wakes the hands-free listener
    } else if (recognition.listening) {
      recognition.stop();
    } else {
      synthesis.cancel();
      recognition.start();
    }
  }, [recognition, synthesis, wake]);

  const clear = useCallback(async () => {
    synthesis.cancel();
    setMessages([]);
    setSelected(null);
    try {
      await api.resetContext(session);
    } catch {
      /* ignore */
    }
  }, [session, synthesis]);

  // ---------------------------------------------------------------- greeting
  useEffect(() => {
    if (!loaded || greeted.current) return;
    greeted.current = true;
    const name = settings.user_name ? `, ${settings.user_name}` : "";
    const hint = settings.wake_word_enabled ? 'Just say "Nova" followed by a command' : "Ask me anything — try the microphone";
    const greeting: ChatMessage = {
      id: uid(),
      role: "system",
      tone: "info",
      text: `${greetingFor()}${name}! I'm ${settings.assistant_name}. ${hint} or type below.`,
      time: nowIso(),
    };
    setMessages((prev) => (prev.length ? prev : [greeting]));
  }, [loaded, settings.user_name, settings.assistant_name, settings.wake_word_enabled]);

  // ---------------------------------------------------------------- polling
  useInterval(refreshTasks, 5000, [online]);

  useInterval(
    async () => {
      if (!online) return;
      try {
        const items = await api.notifications();
        for (const n of items.reverse()) {
          await api.markNotificationRead(n.id);
          pushToast({ title: n.title, message: n.message, kind: n.kind });
          playChime();
          synthesis.speak(`${n.title}. ${n.message}`, `note-${n.id}`);
          setMessages((prev) => [...prev, { id: uid(), role: "system", tone: "info", text: `${n.title}: ${n.message}`, time: nowIso() }]);
        }
        if (items.length) refreshTasks();
      } catch {
        /* offline */
      }
    },
    2500,
    [online],
  );

  const status: AssistantStatus = recognition.listening || wake.state === "awake"
    ? "listening"
    : busy
      ? "processing"
      : synthesis.speaking
        ? "speaking"
        : "idle";

  const value: AssistantContextValue = {
    sessionId: session,
    messages,
    status,
    busy,
    selected,
    selectResult: setSelected,
    send,
    clear,
    recognition,
    synthesis,
    wake,
    toggleListening,
    timers,
    reminders,
    refreshTasks,
    draft,
    setDraft,
    toasts,
    dismissToast,
    pushToast,
  };
  return <AssistantContext.Provider value={value}>{children}</AssistantContext.Provider>;
}

export function useAssistant() {
  const ctx = useContext(AssistantContext);
  if (!ctx) throw new Error("useAssistant must be used inside AssistantProvider");
  return ctx;
}

import { AlarmClock, Bell, Calculator, Clock, Target } from "lucide-react";
import { useAssistant } from "../../context/AssistantContext";
import { useSystem } from "../../context/SystemContext";

/*
 * Quick actions send real utterances through the full ML pipeline (source = quick_action).
 * Ones without parameters ("Set a timer") deliberately trigger Nova's clarification
 * question, so the follow-up answer is handled by the context manager.
 */
const ACTIONS = [
  { label: "What time is it?", text: "What time is it?", icon: Clock },
  { label: "Set timer", text: "Set a timer", icon: AlarmClock },
  { label: "Calculate", text: "Calculate", icon: Calculator },
  { label: "Create reminder", text: "Create a reminder", icon: Bell },
  { label: "Focus mode", text: "Start focus mode", icon: Target },
];

export function QuickActions() {
  const { send, busy } = useAssistant();
  const { online } = useSystem();
  return (
    <div className="flex flex-wrap gap-2">
      {ACTIONS.map(({ label, text, icon: Icon }) => (
        <button
          key={label}
          type="button"
          disabled={busy || !online}
          onClick={() => send(text, "quick_action")}
          className="group flex grow basis-[150px] items-center gap-2.5 whitespace-nowrap rounded-xl border border-line/70 bg-surface2/60 px-3 py-2.5 text-left text-sm text-ink2 transition hover:border-accent/40 hover:bg-surface3 hover:text-ink disabled:opacity-50"
        >
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-accent/10 text-accent transition group-hover:bg-accent/20">
            <Icon size={16} />
          </span>
          {label}
        </button>
      ))}
    </div>
  );
}

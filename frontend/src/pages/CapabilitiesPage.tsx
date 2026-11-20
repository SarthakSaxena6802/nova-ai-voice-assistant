import {
  AlarmClock, Bell, Calculator, Calendar, Clock, CloudSun, Globe, HandMetal, HelpCircle, Lock, MessageSquareText, Play, Sparkles, Target,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge, Card, EmptyState } from "../components/ui/primitives";
import { useAssistant } from "../context/AssistantContext";
import { api } from "../services/api";
import type { CapabilitiesResponse } from "../types/api";

const ICONS: Record<string, typeof Clock> = {
  GREETING: HandMetal,
  GET_TIME: Clock,
  GET_DATE: Calendar,
  CALCULATE: Calculator,
  SET_TIMER: AlarmClock,
  CREATE_REMINDER: Bell,
  FOCUS_MODE: Target,
  OPEN_WEBSITE: Globe,
  WEATHER_QUERY: CloudSun,
  ASK_QUESTION: MessageSquareText,
};

export default function CapabilitiesPage() {
  const [data, setData] = useState<CapabilitiesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { send } = useAssistant();
  const navigate = useNavigate();

  useEffect(() => {
    api.capabilities().then(setData).catch((e) => setError(e.message));
  }, []);

  const tryIt = (text: string) => {
    navigate("/assistant");
    send(text, "text");
  };

  if (error) return <Card><EmptyState icon={HelpCircle} title="Couldn't load capabilities">{error}</EmptyState></Card>;

  return (
    <div className="flex flex-col gap-5">
      <Card title="What Nova can do" icon={Sparkles}>
        <p className="max-w-3xl text-sm leading-relaxed text-ink2">
          Each capability is an <span className="text-ink">intent</span> the ML model was trained to recognise. When the classifier is
          confident enough, the decision engine routes the request to the matching action handler. Click an example to try it.
        </p>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {(data?.capabilities ?? []).map((c) => {
          const Icon = ICONS[c.intent] ?? Sparkles;
          return (
            <div key={c.intent} className="card flex flex-col p-5">
              <div className="flex items-start gap-3">
                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent/10 text-accent">
                  <Icon size={19} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold">{c.name}</h3>
                    <Badge tone={c.available ? "good" : "bad"}>{c.available ? "Available" : "Unavailable"}</Badge>
                  </div>
                  <div className="mt-0.5 font-mono text-[11px] text-muted">{c.intent}</div>
                </div>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-ink2">{c.description}</p>
              <p className="mt-1.5 text-xs text-muted">{c.status}</p>
              <div className="mt-4 flex flex-wrap gap-1.5">
                {c.examples.map((ex) => (
                  <button key={ex} type="button" onClick={() => tryIt(ex)} className="chip transition hover:border-accent/40 hover:text-ink">
                    <Play size={10} /> {ex}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {data && (
        <Card title="Website allow-list" icon={Lock}>
          <p className="mb-3 text-sm text-ink2">
            For safety, Nova can only open these sites. Natural language can never produce an arbitrary URL or run a command.
          </p>
          <div className="flex flex-wrap gap-2">
            {data.websites.map((w) => (
              <a key={w.key} href={w.url} target="_blank" rel="noopener noreferrer" className="chip hover:text-ink">
                <Globe size={12} /> {w.name}
              </a>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

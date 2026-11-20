import { ArrowUpRight, MessageCircle, ScanSearch, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { AssistantComposer, AssistantHero } from "../components/assistant/AssistantPanel";
import { MessageList } from "../components/assistant/MessageList";
import { QuickActions } from "../components/assistant/QuickActions";
import { DecisionInspector, fromResult } from "../components/inspector/DecisionInspector";
import { FocusCard, RemindersCard, TimersCard } from "../components/tasks/ActiveTasks";
import { Card } from "../components/ui/primitives";
import { useAssistant } from "../context/AssistantContext";

export default function DashboardPage() {
  const { selected, messages } = useAssistant();
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
      <div className="flex min-w-0 flex-col gap-5">
        <Card
          title="Assistant"
          icon={MessageCircle}
          action={
            <Link to="/assistant" className="btn-ghost px-2 py-1 text-xs">
              Open full view <ArrowUpRight size={13} />
            </Link>
          }
        >
          <div className="grid gap-5 lg:grid-cols-[180px_minmax(0,1fr)]">
            <div className="flex items-center justify-center lg:border-r lg:border-line/60 lg:pr-5">
              <AssistantHero />
            </div>
            <div className="flex min-w-0 flex-col gap-4">
              <div className="max-h-[300px] min-h-[180px] overflow-y-auto pr-1">
                {messages.length ? (
                  <MessageList limit={8} />
                ) : (
                  <p className="pt-10 text-center text-sm text-muted">Your recent conversation will appear here.</p>
                )}
              </div>
              <AssistantComposer />
            </div>
          </div>
        </Card>

        <Card title="Quick actions" icon={Zap}>
          <QuickActions />
        </Card>

        <div className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">
          <FocusCard />
          <TimersCard />
          <RemindersCard limit={4} />
        </div>
      </div>

      <Card
        title="AI Decision Inspector"
        icon={ScanSearch}
        className="h-fit xl:sticky xl:top-6"
        action={
          <Link to="/assistant" className="btn-ghost px-2 py-1 text-xs">
            Details <ArrowUpRight size={13} />
          </Link>
        }
      >
        <DecisionInspector data={selected ? fromResult(selected) : null} compact />
      </Card>
    </div>
  );
}

import { MessageCircle, ScanSearch } from "lucide-react";
import { AssistantComposer, AssistantHero } from "../components/assistant/AssistantPanel";
import { MessageList } from "../components/assistant/MessageList";
import { DecisionInspector } from "../components/inspector/DecisionInspector";
import { RemindersCard, TimersCard } from "../components/tasks/ActiveTasks";
import { Card } from "../components/ui/primitives";
import { useAssistant } from "../context/AssistantContext";

export default function HomePage() {
  const { selected, messages } = useAssistant();
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,460px)]">
      <div className="flex min-w-0 flex-col gap-5">
        <Card title="Assistant" icon={MessageCircle}>
          <div className="flex h-[calc(100vh-420px)] min-h-[380px] flex-col gap-4">
            <div className="min-h-0 flex-1 overflow-y-auto pr-1">
              {messages.length ? (
                <MessageList />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <AssistantHero />
                </div>
              )}
            </div>
            {messages.length > 0 && (
              <div className="flex justify-center">
                <div className="scale-75">
                  <AssistantHero />
                </div>
              </div>
            )}
            <AssistantComposer autoFocus />
          </div>
        </Card>
        <div className="grid gap-5 md:grid-cols-2">
          <TimersCard />
          <RemindersCard />
        </div>
      </div>

      <Card title="AI Decision Inspector" icon={ScanSearch} className="h-fit xl:sticky xl:top-6">
        <p className="-mt-1 mb-4 text-xs text-muted">Click any of Nova's replies to see how it was decided.</p>
        <DecisionInspector data={selected} />
      </Card>
    </div>
  );
}

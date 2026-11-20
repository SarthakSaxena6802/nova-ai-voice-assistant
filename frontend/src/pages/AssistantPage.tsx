import { MessageCircle, ScanSearch } from "lucide-react";
import { AssistantComposer, AssistantHero } from "../components/assistant/AssistantPanel";
import { MessageList } from "../components/assistant/MessageList";
import { QuickActions } from "../components/assistant/QuickActions";
import { DecisionInspector, fromResult } from "../components/inspector/DecisionInspector";
import { Card } from "../components/ui/primitives";
import { useAssistant } from "../context/AssistantContext";

export default function AssistantPage() {
  const { selected, messages } = useAssistant();
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,480px)]">
      <Card title="Conversation" icon={MessageCircle} className="flex min-w-0 flex-col">
        <div className="flex h-[calc(100vh-260px)] min-h-[520px] flex-col gap-4">
          <div className="min-h-0 flex-1 overflow-y-auto pr-1">
            {messages.length ? (
              <MessageList />
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-6">
                <AssistantHero />
                <p className="max-w-md text-center text-sm text-muted">
                  Speak or type a command. Every reply can be clicked to see exactly how Nova's model and decision engine
                  arrived at it.
                </p>
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
          <QuickActions />
          <AssistantComposer autoFocus />
        </div>
      </Card>

      <Card title="AI Decision Inspector" icon={ScanSearch} className="h-fit xl:sticky xl:top-6">
        <p className="-mt-1 mb-4 text-xs text-muted">
          {selected ? "Showing the selected reply. Click any of Nova's messages to inspect it." : ""}
        </p>
        <DecisionInspector data={selected ? fromResult(selected) : null} />
      </Card>
    </div>
  );
}

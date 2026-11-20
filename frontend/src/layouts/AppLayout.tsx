import { AlarmClock, Bell, Target, X } from "lucide-react";
import { Outlet } from "react-router-dom";
import { Header } from "../components/layout/Header";
import { MobileNav, Sidebar } from "../components/layout/Sidebar";
import { useAssistant } from "../context/AssistantContext";
import { useSystem } from "../context/SystemContext";

const KIND_ICON = { timer: AlarmClock, reminder: Bell, focus: Target } as const;

function Toasts() {
  const { toasts, dismissToast } = useAssistant();
  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-50 flex w-[min(380px,calc(100vw-2rem))] flex-col gap-2" aria-live="polite">
      {toasts.map((t) => {
        const Icon = KIND_ICON[t.kind as keyof typeof KIND_ICON] ?? Bell;
        return (
          <div key={t.id} className="card pointer-events-auto flex animate-fade-in items-start gap-3 p-4 shadow-glow">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-accent/15 text-accent">
              <Icon size={18} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold">{t.title}</div>
              <div className="mt-0.5 text-sm text-ink2">{t.message}</div>
            </div>
            <button className="btn-ghost -mr-2 -mt-1 p-1.5" onClick={() => dismissToast(t.id)} aria-label="Dismiss notification">
              <X size={15} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

function OfflineBanner() {
  const { online, checked } = useSystem();
  if (!checked || online) return null;
  return (
    <div className="mb-5 rounded-xl border border-bad/30 bg-bad/10 px-4 py-3 text-sm text-ink">
      <span className="font-semibold text-bad">Backend offline.</span> Start it with{" "}
      <code className="mono rounded bg-surface3 px-1.5 py-0.5">uvicorn app.main:app --reload</code> in the <code className="mono">backend</code>{" "}
      folder. Nova will reconnect automatically.
    </div>
  );
}

export function AppLayout() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <MobileNav />
        <main className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-8 sm:py-8">
          <Header />
          <OfflineBanner />
          <Outlet />
        </main>
      </div>
      <Toasts />
    </div>
  );
}

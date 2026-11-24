import { MessageCircle, Settings } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useSettings } from "../../context/SettingsContext";
import { useSystem } from "../../context/SystemContext";
import { NovaMark } from "../assistant/NovaOrb";

const NAV = [
  { to: "/", label: "Assistant", icon: MessageCircle, end: true },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const { settings } = useSettings();
  const { health } = useSystem();
  return (
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line/70 bg-surface/60 px-3 py-5 backdrop-blur md:flex">
      <div className="mb-8 flex items-center gap-3 px-2">
        <NovaMark size={34} />
        <div>
          <div className="text-[15px] font-semibold tracking-tight">{settings.assistant_name}</div>
          <div className="text-[11px] text-muted">AI voice assistant</div>
        </div>
      </div>
      <nav className="flex flex-col gap-1">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                isActive ? "bg-accent/10 font-medium text-ink shadow-[inset_2px_0_0_rgb(var(--accent))]" : "text-ink2 hover:bg-surface3 hover:text-ink"
              }`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto rounded-xl border border-line/70 bg-surface2/70 p-3 text-[11px] leading-relaxed text-muted">
        <div className="font-medium text-ink2">Intent model</div>
        {health?.model.loaded ? (
          <>
            TF-IDF + Logistic Regression
            <br />
            v{health.model.version} · {((health.model.accuracy ?? 0) * 100).toFixed(1)}% test acc.
          </>
        ) : (
          "Not loaded"
        )}
      </div>
    </aside>
  );
}

export function MobileNav() {
  return (
    <nav className="sticky top-0 z-30 flex gap-1 overflow-x-auto border-b border-line bg-surface/90 px-3 py-2 backdrop-blur md:hidden">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs ${isActive ? "bg-accent/15 text-ink" : "text-ink2"}`
          }
        >
          <Icon size={14} />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

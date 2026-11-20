import type { AssistantStatus } from "../../context/AssistantContext";

export function NovaMark({ size = 32 }: { size?: number }) {
  return (
    <div
      className="relative shrink-0 rounded-full"
      style={{
        width: size,
        height: size,
        background: "radial-gradient(circle at 35% 30%, #d4ceff 0%, rgb(var(--accent)) 45%, rgb(var(--accent-2)) 100%)",
      }}
    >
      <div className="absolute inset-[30%] rounded-full bg-white/85" />
    </div>
  );
}

const STATUS_COPY: Record<AssistantStatus, string> = {
  idle: "Ready",
  listening: "Listening…",
  processing: "Thinking…",
  speaking: "Speaking…",
};

/** Animated avatar whose appearance reflects the assistant state. */
export function NovaOrb({ status, size = 132 }: { status: AssistantStatus; size?: number }) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative grid place-items-center" style={{ width: size, height: size }}>
        {status === "listening" && (
          <>
            <span className="absolute inset-0 animate-ripple rounded-full border-2 border-accent/60" />
            <span className="absolute inset-0 animate-ripple rounded-full border-2 border-accent2/50 [animation-delay:0.8s]" />
          </>
        )}
        {status === "processing" && (
          <span
            className="absolute inset-[-6px] animate-spin-slow rounded-full"
            style={{ background: "conic-gradient(from 0deg, transparent 0 70%, rgb(var(--accent)) 100%)", mask: "radial-gradient(circle, transparent 62%, black 63%)", WebkitMask: "radial-gradient(circle, transparent 62%, black 63%)" }}
          />
        )}
        <div
          className={`relative rounded-full transition-all duration-500 ${status === "idle" ? "animate-breathe" : ""}`}
          style={{
            width: size * 0.78,
            height: size * 0.78,
            background:
              "radial-gradient(circle at 32% 28%, rgba(255,255,255,0.9) 0%, rgba(214,208,255,0.75) 14%, rgb(var(--accent)) 52%, rgb(var(--accent-2)) 100%)",
            boxShadow:
              status === "idle"
                ? "0 0 40px -10px rgb(var(--accent) / 0.55)"
                : "0 0 60px -6px rgb(var(--accent) / 0.75), 0 0 24px -4px rgb(var(--accent-2) / 0.6)",
            transform: status === "speaking" ? "scale(1.05)" : undefined,
          }}
        >
          {status === "speaking" && (
            <div className="absolute inset-0 flex items-center justify-center gap-1">
              {[0, 1, 2, 3, 4].map((i) => (
                <span
                  key={i}
                  className="w-1 rounded-full bg-white/90"
                  style={{ height: 10 + (i % 2) * 10, animation: `breathe 0.${6 + i}s ease-in-out infinite` }}
                />
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="text-xs font-medium uppercase tracking-[0.14em] text-muted">{STATUS_COPY[status]}</div>
    </div>
  );
}

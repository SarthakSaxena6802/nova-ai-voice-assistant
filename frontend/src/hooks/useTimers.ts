import { useEffect, useRef, useState } from "react";

/** Calls `fn` immediately and then every `ms` milliseconds (paused while the tab is hidden). */
export function useInterval(fn: () => void, ms: number, deps: unknown[] = []) {
  const fnRef = useRef(fn);
  fnRef.current = fn;
  useEffect(() => {
    fnRef.current();
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") fnRef.current();
    }, ms);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, ...deps]);
}

/** Re-renders every `ms` and returns the current time – used for live countdowns. */
export function useNow(ms = 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), ms);
    return () => window.clearInterval(id);
  }, [ms]);
  return now;
}

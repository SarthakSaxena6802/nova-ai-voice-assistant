import { useCallback, useEffect, useRef, useState } from "react";
import { playChime } from "../utils/sound";
import { ERROR_MESSAGES, getCtor } from "./useSpeechRecognition";

/*
 * Hands-free mode: one continuous recognizer listens while the tab is open and only acts on
 * speech that contains "Nova". "Nova, set a timer" runs immediately; "Nova" alone waits
 * AWAKE_MS for the command. Everything else is ignored.
 */

const AWAKE_MS = 8000;
const WAKE = /\b(?:(?:hey|hi|ok|okay)\s+)?nova\b[\s,.!?]*/i;

/** "hey nova, set a timer" -> { woke: true, command: "set a timer" } */
export function splitWake(text: string): { woke: boolean; command: string } {
  const m = WAKE.exec(text);
  return m ? { woke: true, command: text.slice(m.index + m[0].length).trim() } : { woke: false, command: "" };
}

export type WakeState = "off" | "idle" | "awake";

export interface WakeWordState {
  state: WakeState;
  heard: string;
  error: string | null;
  wakeNow: () => void;
}

export function useWakeWord(active: boolean, ignore: boolean, onCommand: (text: string) => void): WakeWordState {
  const [state, setState] = useState<WakeState>("off");
  const [heard, setHeard] = useState("");
  const [error, setError] = useState<string | null>(null);
  const awakeUntil = useRef(0);
  const cb = useRef(onCommand);
  cb.current = onCommand;
  const ignoreRef = useRef(ignore);
  ignoreRef.current = ignore;

  const wakeNow = useCallback(() => {
    awakeUntil.current = Date.now() + AWAKE_MS;
    setState("awake");
    playChime();
    window.setTimeout(() => {
      if (Date.now() >= awakeUntil.current) setState((s) => (s === "awake" ? "idle" : s));
    }, AWAKE_MS + 100);
  }, []);

  useEffect(() => {
    const Ctor = getCtor();
    if (!active || !Ctor) {
      setState("off");
      return;
    }
    let stopped = false;
    let retry: number | undefined;
    let rec: InstanceType<NonNullable<ReturnType<typeof getCtor>>> | null = null;

    const fire = (command: string) => {
      awakeUntil.current = 0;
      setState("idle");
      setHeard("");
      cb.current(command);
    };

    const run = () => {
      rec = new Ctor();
      rec.lang = navigator.language || "en-US";
      rec.continuous = true;
      rec.interimResults = true;
      rec.onresult = (e) => {
        for (let i = e.resultIndex; i < e.results.length; i++) {
          if (ignoreRef.current) continue; // Nova is talking or thinking: don't hear itself
          const r = e.results[i];
          const text = r[0].transcript.trim();
          const awake = Date.now() < awakeUntil.current;
          const { woke, command } = splitWake(text);
          if (!r.isFinal) {
            if (woke || awake) setHeard(text);
          } else if (woke && command) {
            fire(command);
          } else if (woke) {
            setHeard("");
            wakeNow();
          } else if (awake && text) {
            fire(text);
          }
        }
      };
      rec.onerror = (e) => {
        if (["not-allowed", "service-not-allowed", "audio-capture"].includes(e.error)) {
          stopped = true;
          setError(ERROR_MESSAGES[e.error]);
          setState("off");
        }
      };
      // Chrome ends continuous sessions after silence or ~1 min; just start a new one.
      rec.onend = () => {
        if (!stopped) retry = window.setTimeout(run, 300);
      };
      try {
        rec.start();
        setError(null);
        setState((s) => (s === "off" ? "idle" : s));
      } catch {
        retry = window.setTimeout(run, 1000);
      }
    };

    run();
    return () => {
      stopped = true;
      window.clearTimeout(retry);
      rec?.abort();
      setState("off");
    };
  }, [active, wakeNow]);

  return { state, heard, error, wakeNow };
}

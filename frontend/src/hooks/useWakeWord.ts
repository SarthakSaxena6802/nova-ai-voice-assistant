import { useCallback, useEffect, useRef, useState } from "react";
import { playChime } from "../utils/sound";
import { ERROR_MESSAGES, getCtor } from "./useSpeechRecognition";

/*
 * Hands-free mode: one continuous recognizer listens while `active` and only acts on speech
 * that contains "Nova". "Nova, set a timer" runs immediately; "Nova" alone waits AWAKE_MS for
 * the command. The caller sets `active` to false while Nova is thinking or speaking, so the
 * microphone is closed then (Nova can't hear itself) and a fresh session starts afterwards.
 */

const AWAKE_MS = 8000;
const WAKE = /\b(?:(?:hey|hi|ok|okay)\s+)?nova\b[\s,.!?]*/i;
// Only these mean "the microphone can't be used at all"; every other error is retried.
const FATAL = ["not-allowed", "service-not-allowed"];

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

export function useWakeWord(active: boolean, onCommand: (text: string) => void): WakeWordState {
  const [state, setState] = useState<WakeState>("off");
  const [heard, setHeard] = useState("");
  const [error, setError] = useState<string | null>(null);
  const awakeUntil = useRef(0);
  const cb = useRef(onCommand);
  cb.current = onCommand;

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
    let failed = false;
    let retry: number | undefined;
    let rec: InstanceType<NonNullable<ReturnType<typeof getCtor>>> | null = null;

    const fire = (command: string) => {
      awakeUntil.current = 0;
      setState("idle");
      setHeard("");
      cb.current(command);
    };

    const run = () => {
      failed = false;
      rec = new Ctor();
      rec.lang = navigator.language || "en-US";
      rec.continuous = true;
      rec.interimResults = true;
      rec.onstart = () => {
        setError(null);
        setState((s) => (s === "off" ? "idle" : s)); // only claim "listening" once the browser confirms it
      };
      rec.onresult = (e) => {
        for (let i = e.resultIndex; i < e.results.length; i++) {
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
        if (FATAL.includes(e.error)) {
          stopped = true;
          setError(ERROR_MESSAGES[e.error]);
          setState("off");
        } else {
          failed = true; // e.g. "audio-capture" while the speakers play, "network", "no-speech"
        }
      };
      // Chrome ends sessions after silence, errors or ~1 min; start a new one (slower after an error).
      rec.onend = () => {
        if (!stopped) retry = window.setTimeout(run, failed ? 1500 : 250);
      };
      try {
        rec.start();
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

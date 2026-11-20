import { useCallback, useEffect, useRef, useState } from "react";

/*
 * Text-to-speech through the browser's speechSynthesis. Wrapped in a hook so another
 * TTS engine can be swapped in behind the same { speak, cancel, speaking } interface.
 */

export interface SpeechSynthesisState {
  supported: boolean;
  speaking: boolean;
  voices: SpeechSynthesisVoice[];
  speak: (text: string, key?: string) => void;
  cancel: () => void;
}

export function useSpeechSynthesis(opts: { enabled: boolean; voiceName: string; rate: number }): SpeechSynthesisState {
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [speaking, setSpeaking] = useState(false);
  const spokenKeys = useRef<Set<string>>(new Set());
  const optsRef = useRef(opts);
  optsRef.current = opts;

  useEffect(() => {
    if (!supported) return;
    const load = () => setVoices(window.speechSynthesis.getVoices());
    load();
    window.speechSynthesis.addEventListener("voiceschanged", load);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", load);
  }, [supported]);

  const cancel = useCallback(() => {
    if (!supported) return;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  const speak = useCallback(
    (text: string, key?: string) => {
      const { enabled, voiceName, rate } = optsRef.current;
      if (!supported || !enabled || !text.trim()) return;
      // Never speak the same response twice (re-renders, React strict mode, etc.)
      if (key) {
        if (spokenKeys.current.has(key)) return;
        spokenKeys.current.add(key);
      }
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text.replace(/[*_#`]/g, ""));
      const voice = window.speechSynthesis.getVoices().find((v) => v.name === voiceName);
      if (voice) utterance.voice = voice;
      utterance.rate = rate;
      utterance.onstart = () => setSpeaking(true);
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      window.speechSynthesis.speak(utterance);
    },
    [supported],
  );

  return { supported, speaking, voices, speak, cancel };
}

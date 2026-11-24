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
  // Chrome may garbage-collect an utterance mid-speech and then never fire `onend`; holding a reference prevents that.
  const current = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    if (!supported) return;
    const load = () => setVoices(window.speechSynthesis.getVoices());
    load();
    window.speechSynthesis.addEventListener("voiceschanged", load);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", load);
  }, [supported]);

  // Fallback for missed `onend` events: trust the browser's own flag.
  useEffect(() => {
    if (!speaking || !supported) return;
    const id = window.setInterval(() => {
      if (!window.speechSynthesis.speaking && !window.speechSynthesis.pending) setSpeaking(false);
    }, 400);
    return () => window.clearInterval(id);
  }, [speaking, supported]);

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
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      current.current = utterance;
      setSpeaking(true); // set immediately so the wake-word listener pauses before the audio starts
      window.speechSynthesis.speak(utterance);
    },
    [supported],
  );

  return { supported, speaking, voices, speak, cancel };
}

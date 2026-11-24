import { Brain, Cpu, RotateCcw, Save, SlidersHorizontal, Volume2 } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Badge, Card, ConfirmButton, Field, Toggle } from "../components/ui/primitives";
import { useAssistant } from "../context/AssistantContext";
import { useSettings } from "../context/SettingsContext";
import { useSystem } from "../context/SystemContext";
import { api } from "../services/api";
import type { NovaSettings } from "../types/api";
import { pct } from "../utils/format";

export default function SettingsPage() {
  const { settings, update, replace } = useSettings();
  const { health, online } = useSystem();
  const { synthesis, recognition, pushToast } = useAssistant();
  const [form, setForm] = useState<NovaSettings>(settings);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setForm(settings), [settings]);
  const dirty = useMemo(() => JSON.stringify(form) !== JSON.stringify(settings), [form, settings]);
  const set = <K extends keyof NovaSettings>(key: K, value: NovaSettings[K]) => setForm((f) => ({ ...f, [key]: value }));

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await update(form);
      pushToast({ title: "Settings saved", message: "Your preferences were stored.", kind: "system" });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const voices = synthesis.voices;
  const testVoice = () => {
    if (!synthesis.supported) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(`Hi${form.user_name ? " " + form.user_name : ""}, I'm ${form.assistant_name}. This is how I sound.`);
    const v = voices.find((x) => x.name === form.voice_name);
    if (v) u.voice = v;
    u.rate = form.speech_rate;
    window.speechSynthesis.speak(u);
  };

  return (
    <div className="flex max-w-3xl flex-col gap-5 pb-24">
      <Section icon={SlidersHorizontal} title="General">
        <Field label="Assistant name">
          <input className="input" value={form.assistant_name} maxLength={30} onChange={(e) => set("assistant_name", e.target.value)} />
        </Field>
        <Field label="Your name" hint="Used in greetings. Optional.">
          <input className="input" value={form.user_name} maxLength={40} onChange={(e) => set("user_name", e.target.value)} placeholder="e.g. Alex" />
        </Field>
        <Field label="Theme">
          <Segmented value={form.theme} options={[["dark", "Dark"], ["light", "Light"]]} onChange={(v) => set("theme", v as NovaSettings["theme"])} />
        </Field>
      </Section>

      <Section icon={Volume2} title="Voice">
        <Field label='Hands-free: wake on "Nova"' hint="Listens while this tab is open and only acts on speech containing “Nova”. In Chrome the audio is processed by Google’s speech service.">
          <Toggle label="Hands-free wake word" checked={form.wake_word_enabled} onChange={(v) => set("wake_word_enabled", v)} disabled={!recognition.supported} />
        </Field>
        <Field label="Spoken responses" hint={synthesis.supported ? "Nova reads its replies aloud." : "Speech synthesis isn't available in this browser."}>
          <Toggle label="Spoken responses" checked={form.voice_enabled} onChange={(v) => set("voice_enabled", v)} disabled={!synthesis.supported} />
        </Field>
        <Field label="Voice" hint={`${voices.length} voices available in this browser.`}>
          <select className="input" value={form.voice_name} onChange={(e) => set("voice_name", e.target.value)} disabled={!voices.length}>
            <option value="">Browser default</option>
            {voices.map((v) => (
              <option key={v.name} value={v.name}>
                {v.name} ({v.lang})
              </option>
            ))}
          </select>
        </Field>
        <Field label={`Speech speed · ${form.speech_rate.toFixed(1)}×`}>
          <div className="flex items-center gap-3">
            <input type="range" min={0.5} max={2} step={0.1} value={form.speech_rate} onChange={(e) => set("speech_rate", Number(e.target.value))} className="w-full accent-[rgb(var(--accent))]" />
            <button className="btn-outline px-3 py-1.5 text-xs" onClick={testVoice} disabled={!synthesis.supported}>Test</button>
          </div>
        </Field>
        <Field label="Send mic commands automatically" hint="Off: what you said is placed in the text box so you can edit it first (mic button only).">
          <Toggle label="Auto-send voice" checked={form.auto_send_voice} onChange={(v) => set("auto_send_voice", v)} />
        </Field>
      </Section>

      <Section icon={Brain} title="Decision engine">
        <Field label={`Execute threshold · ${pct(form.execute_threshold, 0)}`} hint="At or above this confidence Nova acts directly.">
          <input type="range" min={0.3} max={0.99} step={0.01} value={form.execute_threshold}
            onChange={(e) => set("execute_threshold", Math.max(Number(e.target.value), form.clarify_threshold + 0.05))} className="w-full accent-[rgb(var(--accent))]" />
        </Field>
        <Field label={`Clarification threshold · ${pct(form.clarify_threshold, 0)}`} hint="Between the two thresholds Nova asks for confirmation; below it, Nova says it didn't understand.">
          <input type="range" min={0.05} max={0.9} step={0.01} value={form.clarify_threshold}
            onChange={(e) => set("clarify_threshold", Math.min(Number(e.target.value), form.execute_threshold - 0.05))} className="w-full accent-[rgb(var(--accent))]" />
        </Field>
        <Field label={`Context memory · ${form.context_timeout_seconds}s`} hint="How long Nova remembers a pending question or the last action for follow-ups.">
          <input type="range" min={15} max={600} step={15} value={form.context_timeout_seconds} onChange={(e) => set("context_timeout_seconds", Number(e.target.value))} className="w-full accent-[rgb(var(--accent))]" />
        </Field>
      </Section>

      <Section icon={Cpu} title="System">
        <Field label="Backend">
          <Badge tone={online ? "good" : "bad"}>{online ? `Online · v${health?.version}` : "Offline"}</Badge>
        </Field>
        <Field label="Intent model" hint={health?.model.name ?? undefined}>
          <Badge tone={health?.model.loaded ? "good" : "bad"}>
            {health?.model.loaded ? `v${health.model.version} · ${pct(health.model.accuracy)} test accuracy` : "Not loaded"}
          </Badge>
        </Field>
        <Field label="Defaults">
          <ConfirmButton className="btn-outline" confirmLabel="Reset all settings?" onConfirm={async () => replace(await api.resetSettings())}>
            <RotateCcw size={14} /> Reset settings
          </ConfirmButton>
        </Field>
      </Section>

      {(dirty || error) && (
        <div className="fixed inset-x-0 bottom-4 z-40 mx-auto flex w-[min(640px,calc(100vw-2rem))] items-center justify-between gap-3 rounded-2xl border border-line bg-surface px-4 py-3 shadow-glow md:left-60">
          <span className={`text-sm ${error ? "text-bad" : "text-ink2"}`}>{error ?? "You have unsaved changes."}</span>
          <div className="flex gap-2">
            <button className="btn-ghost" onClick={() => { setForm(settings); setError(null); }}>Discard</button>
            <button className="btn-primary" onClick={save} disabled={saving || !dirty}><Save size={15} /> {saving ? "Saving…" : "Save"}</button>
          </div>
        </div>
      )}
    </div>
  );
}

function Section({ icon, title, children }: { icon: typeof Brain; title: string; children: ReactNode }) {
  return (
    <Card title={title} icon={icon}>
      <div className="-my-2 divide-y divide-line/60">{children}</div>
    </Card>
  );
}

function Segmented({ value, options, onChange }: { value: string; options: [string, string][]; onChange: (v: string) => void }) {
  return (
    <div className="inline-flex rounded-xl border border-line bg-surface2 p-1">
      {options.map(([v, label]) => (
        <button key={v} type="button" onClick={() => onChange(v)}
          className={`rounded-lg px-3 py-1.5 text-sm transition ${value === v ? "bg-accent text-white" : "text-ink2 hover:text-ink"}`}>
          {label}
        </button>
      ))}
    </div>
  );
}

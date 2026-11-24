// Types mirroring the FastAPI response models.

export type Decision = "EXECUTE" | "CONFIRM" | "CLARIFY" | "UNKNOWN" | "CANCELLED";
export type InputSource = "text" | "voice" | "quick_action";

export interface IntentScore {
  intent: string;
  confidence: number;
}

export interface FeatureContribution {
  feature: string;
  kind: "word" | "char" | string;
  weight: number;
}

export interface PipelineStep {
  stage: string;
  title: string;
  detail: string;
  status: "ok" | "warn" | "error" | "skip";
  ms: number | null;
}

export interface ProcessResult {
  timestamp: string;
  session_id: string;
  source: InputSource;
  input: string;
  normalized: string;
  model_input: string;
  intent: string;
  confidence: number;
  predicted_intent: string;
  top_intents: IntentScore[];
  alternatives: IntentScore[];
  explanation: FeatureContribution[];
  entities: Record<string, unknown>;
  missing_entities: string[];
  thresholds: { execute: number; clarify: number };
  decision: Decision;
  decision_reason: string;
  action: string | null;
  response: string;
  success: boolean;
  data: Record<string, any>;
  context_used: string | null;
  context: { pending: any | null; last_action: any | null };
  notes: string[];
  pipeline: PipelineStep[];
  processing_ms: number;
}

export interface Health {
  status: "ok" | "degraded";
  version: string;
  uptime_seconds: number;
  database: { ok: boolean };
  model: { loaded: boolean; version: string | null; name: string | null; accuracy: number | null; error: string | null };
}

export interface Timer {
  id: number;
  label: string;
  duration_seconds: number;
  created_at: string;
  ends_at: string;
  status: "active" | "completed" | "cancelled";
  finished_at: string | null;
  remaining_seconds: number;
}

export interface Reminder {
  id: number;
  message: string;
  due_at: string;
  created_at: string;
  status: "pending" | "completed";
  notified: boolean;
  completed_at: string | null;
  overdue: boolean;
}

export interface NotificationItem {
  id: number;
  created_at: string;
  kind: "timer" | "reminder" | "system";
  title: string;
  message: string;
  ref_id: number | null;
  read: boolean;
}

export interface NovaSettings {
  assistant_name: string;
  user_name: string;
  theme: "dark" | "light";
  voice_enabled: boolean;
  voice_name: string;
  speech_rate: number;
  auto_send_voice: boolean;
  wake_word_enabled: boolean;
  execute_threshold: number;
  clarify_threshold: number;
  context_timeout_seconds: number;
}

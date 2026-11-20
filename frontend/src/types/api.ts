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
  id: number | null;
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
  app: string;
  version: string;
  uptime_seconds: number;
  database: { ok: boolean };
  model: { loaded: boolean; version: string | null; name: string | null; accuracy: number | null; error: string | null };
  services: {
    llm: { provider: string | null; model: string | null; configured: boolean };
    weather: { enabled: boolean; provider: string };
    knowledge_base: { entries: number };
    open_browser_on_server: boolean;
  };
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

export interface FocusSession {
  id: number;
  duration_seconds: number;
  started_at: string;
  ends_at: string;
  status: "active" | "completed" | "stopped";
  ended_at: string | null;
  remaining_seconds: number;
}

export interface FocusStatus {
  active: FocusSession | null;
  completed_sessions: number;
  completed_today: number;
  total_focus_minutes: number;
}

export interface NotificationItem {
  id: number;
  created_at: string;
  kind: "timer" | "reminder" | "focus" | "system";
  title: string;
  message: string;
  ref_id: number | null;
  read: boolean;
}

export interface NovaSettings {
  assistant_name: string;
  user_name: string;
  theme: "dark" | "light";
  start_page: "dashboard" | "assistant";
  greet_on_startup: boolean;
  voice_enabled: boolean;
  voice_name: string;
  speech_rate: number;
  auto_send_voice: boolean;
  execute_threshold: number;
  clarify_threshold: number;
  llm_enabled: boolean;
  context_timeout_seconds: number;
  focus_default_minutes: number;
  weather_city: string;
  temperature_unit: "celsius" | "fahrenheit";
}

export interface Capability {
  intent: string;
  name: string;
  description: string;
  examples: string[];
  requires: string[];
  available: boolean;
  status: string;
}

export interface CapabilitiesResponse {
  capabilities: Capability[];
  websites: { key: string; name: string; url: string }[];
  intents: string[];
}

export interface HistoryItem {
  id: number;
  created_at: string;
  session_id: string;
  source: InputSource;
  raw_input: string;
  normalized_input: string;
  intent: string;
  confidence: number;
  alternatives: IntentScore[];
  entities: Record<string, unknown>;
  decision: Decision;
  decision_reason: string;
  action: string | null;
  response: string;
  success: boolean;
  context_used: string | null;
  processing_ms: number;
  trace: {
    predicted_intent?: string;
    model_input?: string;
    thresholds?: { execute: number; clarify: number };
    explanation?: FeatureContribution[];
    pipeline?: PipelineStep[];
    missing_entities?: string[];
    notes?: string[];
  };
}

export interface HistoryPage {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface Analytics {
  empty: boolean;
  total: number;
  executed?: number;
  successful?: number;
  failed_actions?: number;
  clarifications?: number;
  confirmations?: number;
  missing_info?: number;
  unknown?: number;
  cancelled?: number;
  context_resolved?: number;
  success_rate?: number;
  execution_rate?: number;
  avg_confidence?: number;
  avg_processing_ms?: number;
  voice_share?: number;
  intent_distribution?: { intent: string; count: number }[];
  decision_distribution?: { decision: string; count: number }[];
  source_distribution?: { source: string; count: number }[];
  confidence_histogram?: { bucket: string; from: number; count: number }[];
  confidence_by_intent?: { intent: string; avg_confidence: number; count: number }[];
  daily?: { date: string; total: number; executed: number }[];
}

export interface ClassMetrics {
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface ModelReport {
  model_version: string;
  model_name: string;
  trained_at: string;
  dataset_size: number;
  class_counts: Record<string, number>;
  train_size: number;
  test_size: number;
  hyperparameters: Record<string, any>;
  metrics: {
    accuracy: number;
    precision_macro: number;
    recall_macro: number;
    f1_macro: number;
    test_mean_confidence: number;
    cv_accuracy_mean: number;
    cv_accuracy_std: number;
    unseen_accuracy: number | null;
  };
  test_metrics: {
    per_class: Record<string, ClassMetrics>;
    confusion_matrix: { labels: string[]; matrix: number[][] };
  };
  misclassified_test_examples: { text: string; expected: string; predicted: string }[];
  unseen_evaluation: { size: number; accuracy: number } | null;
}

export interface ModelInfoResponse {
  info: { loaded: boolean; error: string | null; model_version: string | null; classes: string[] };
  report: ModelReport | null;
}

export interface PredictResponse {
  input: string;
  model_input: string;
  intent: string;
  confidence: number;
  ranking: IntentScore[];
  explanation: FeatureContribution[];
  inference_ms: number;
}

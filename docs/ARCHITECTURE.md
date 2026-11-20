# Nova — Architecture notes

## Request lifecycle (`POST /api/assistant/process`)

| # | Stage | Module | Output |
|---|---|---|---|
| 1 | Validation | `schemas/assistant.py` | `ProcessRequest` (1–500 chars, source, session id) |
| 2 | Normalisation | `nlp/preprocessing.py` | lower-case text, numbers as digits, wake word removed |
| 3 | Classification | `ml/intent_classifier.py` | ranked intent probabilities, top features |
| 4 | Context resolution | `engine/pipeline.py`, `context/manager.py` | slot filling / confirmation / follow-up, or pass |
| 5 | Confidence evaluation | `engine/pipeline.py` | compare with `clarify_threshold` / `execute_threshold` |
| 6 | Entity extraction | `nlp/entities.py` (+ `duration`, `datetime_parser`, `math_expression`, `websites`) | entities + missing slots |
| 7 | Decision | `engine/pipeline.py` | `EXECUTE` · `CONFIRM` · `CLARIFY` · `UNKNOWN` · `CANCELLED` |
| 8 | Action | `actions/registry.py` → handler | `ActionResult {success, message, data, context}` |
| 9 | Persistence | `services/history_service.py` | `interactions` + anonymised `analytics_events` |

Every stage appends a `PipelineStep` (title, detail, status, ms) that the UI renders in the inspector.

## Action interface

```python
class BaseAction(ABC):
    intent: str; name: str; description: str; examples: list[str]; requires: list[str]
    def execute(self, entities: dict, ctx: ActionContext) -> ActionResult: ...
    def available(self, info: dict) -> tuple[bool, str]: ...
```

`ActionRegistry.execute` wraps every handler: an exception becomes
`ActionResult(success=False, error="internal_error")` and the DB session is rolled back, so a broken handler can
never crash a request. `ActionResult.context` (e.g. `{"timer_id": 7}`) is stored as the session's `last_action`.

## Database schema (SQLite)

| Table | Key columns |
|---|---|
| `interactions` | created_at, session_id, source, raw_input, normalized_input, intent, confidence, alternatives (JSON), entities (JSON), decision, decision_reason, action, response, success, context_used, processing_ms, trace (JSON) |
| `analytics_events` | created_at, source, intent, confidence, decision, success, context_used, processing_ms — **no text** |
| `timers` | label, duration_seconds, created_at, ends_at, status (active/completed/cancelled), finished_at |
| `reminders` | message, due_at, created_at, status (pending/completed), notified, completed_at |
| `focus_sessions` | duration_seconds, started_at, ends_at, status (active/completed/stopped), ended_at |
| `notifications` | created_at, kind (timer/reminder/focus/system), title, message, ref_id, read |
| `settings` | key, value (JSON) — validated through `NovaSettings` |

## Background scheduler

`services/scheduler.py` runs inside the FastAPI lifespan as an asyncio task (1 s interval, work done in a thread):
completes due timers and focus sessions, marks due reminders as notified, and writes `notifications` rows. The UI
polls `/api/notifications` every 2.5 s, shows a toast, plays a chime, speaks the message and marks it read.

## Safety rules

- No shell execution anywhere; websites come only from `nlp/websites.py::SAFE_WEBSITES`.
- Calculator: `ast.parse(mode="eval")` + a whitelist interpreter (numbers, `+ - * / % **`, `sqrt/cbrt/abs`),
  exponent and magnitude limits; `eval` is never used.
- Inputs validated by Pydantic (length, enums, session-id pattern, future reminder times, threshold ordering).
- Secrets only in backend env vars; `core/logging.py` redacts key-like strings from every log record.
- Weather/LLM failures produce an honest message, never fabricated data.

## Extending Nova

**New intent:** add examples to `datasets/intents.json` → add an extractor to `nlp/entities.py::EXTRACTORS` (if it
needs parameters) → implement a `BaseAction` and register it in `actions/registry.py` → retrain
(`python ml/train_model.py`) → `POST /api/model/reload`.

**New classifier:** implement `predict(text) -> Prediction` with the same fields as `IntentClassifier`; the rest of
the pipeline is unchanged.

**New LLM provider:** subclass `services/llm/base.py::LLMProvider` and add it to `services/llm/factory.py`.

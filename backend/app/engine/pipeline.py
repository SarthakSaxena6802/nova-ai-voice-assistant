"""Nova's AI decision pipeline.

    input → normalisation → ML intent classification → context resolution
          → confidence evaluation → entity extraction → decision → action → response

Decision rules (thresholds are user settings):

* pending context (an earlier question) is resolved first – slot filling or yes/no confirmation;
* short follow-ups to the previous action ("actually make it 15", "cancel it") are resolved next;
* otherwise the classifier's top intent is evaluated:
    - confidence <  clarify threshold          → UNKNOWN  (ask to rephrase)
    - top intent is UNKNOWN                    → UNKNOWN  (out of scope)
    - clarify ≤ confidence < execute threshold → CONFIRM  (ask "should I go ahead?")
    - confidence ≥ execute threshold:
        required entity missing                → CLARIFY  (ask for it, remember context)
        all present                            → EXECUTE  (run the registered action)
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.actions.base import ActionContext, ActionResult
from app.actions.registry import ActionRegistry
from app.context.manager import ContextManager, ConversationContext, PendingAction
from app.core.logging import get_logger
from app.core.timeutils import humanize_seconds, now
from app.engine import responses as R
from app.ml.intent_classifier import IntentClassifier, Prediction
from app.nlp.datetime_parser import parse_datetime
from app.nlp.duration import bare_number, extract_duration
from app.nlp.entities import EntityResult, extract_entities
from app.nlp.preprocessing import normalize_text
from app.schemas.assistant import (
    FeatureOut,
    IntentScoreOut,
    PipelineStep,
    ProcessRequest,
    ProcessResponse,
    Thresholds,
)
from app.schemas.settings import NovaSettings
from app.services import reminder_service, settings_service, timer_service
from app.services.knowledge_base import KnowledgeBase

log = get_logger("engine")

_FOLLOW_UP_MODIFY = re.compile(
    r"^(?:(?:actually|no|wait|oh|sorry|hmm|okay|ok|please)\s+)*"
    r"(?:(?:make|change|set|update|extend|move|switch)\s+(?:it|that|this|the timer|the reminder)\s*(?:to|for|until)?\s+"
    r"|(?=\d))(?P<rest>.+)$"
)
_FOLLOW_UP_CANCEL = re.compile(r"^(?:(?:actually|no|wait|oh|please)\s+)*(?:cancel|stop|delete|remove|undo)\s+(?:it|that|this)$")
_FOLLOW_UP_GUARD = re.compile(r"^(?:actually|no|wait|oh|sorry|hmm|make|change|set it|update|extend|move|switch|cancel|stop|delete|remove|undo|\d)")


@dataclass
class Outcome:
    intent: str
    decision: str
    reason: str
    response: str
    success: bool = False
    entities: dict[str, Any] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    action: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    context_used: str | None = None
    notes: list[str] = field(default_factory=list)


class Trace:
    def __init__(self) -> None:
        self.steps: list[PipelineStep] = []
        self._t = time.perf_counter()

    def add(self, stage: str, title: str, detail: str, status: str = "ok") -> None:
        t = time.perf_counter()
        self.steps.append(PipelineStep(stage=stage, title=title, detail=detail, status=status, ms=round((t - self._t) * 1000, 2)))
        self._t = t


class AssistantPipeline:
    def __init__(
        self,
        classifier: IntentClassifier,
        registry: ActionRegistry,
        contexts: ContextManager,
        knowledge_base: KnowledgeBase | None = None,
        open_browser_on_server: bool = False,
    ) -> None:
        self.classifier = classifier
        self.registry = registry
        self.contexts = contexts
        self.knowledge_base = knowledge_base
        self.open_browser_on_server = open_browser_on_server

    # ================================================================== entry point
    def process(self, db: Session, req: ProcessRequest) -> ProcessResponse:
        started = time.perf_counter()
        prefs = settings_service.get_settings(db)
        current = now()
        trace = Trace()
        trace.add("input", "Input received", f"{req.source} input: “{req.text}”")

        normalized = normalize_text(req.text)
        trace.add("normalize", "Text normalisation", f"“{normalized}” (lower-case, contractions, number words → digits, wake word removed)")

        prediction = self.classifier.predict(req.text)
        top3 = ", ".join(f"{s.intent} {s.confidence:.1%}" for s in prediction.top(3))
        trace.add("classify", "ML intent classification", f"Model input “{prediction.model_input}” → {top3} ({prediction.inference_ms} ms)")
        log.info("Prediction %r → %s (%.3f)", normalized, prediction.intent, prediction.confidence)

        ctx = self.contexts.get(req.session_id, prefs.context_timeout_seconds)
        outcome: Outcome | None = None
        if ctx.pending:
            outcome = self._resolve_pending(db, ctx, req.text, normalized, prediction, prefs, trace)
        elif ctx.last_action:
            outcome = self._resolve_follow_up(db, ctx, normalized, prediction, prefs, trace)
        else:
            trace.add("context", "Context check", "No pending question or recent action – using the classifier's decision", "skip")
        if outcome is None:
            outcome = self._decide(db, ctx, req.text, normalized, prediction, prefs, trace)

        trace.add("respond", "Response generation", f"“{outcome.response}”")
        log.info("Decision=%s intent=%s action=%s success=%s", outcome.decision, outcome.intent, outcome.action, outcome.success)

        elapsed = round((time.perf_counter() - started) * 1000, 2)
        response = ProcessResponse(
            timestamp=current,
            session_id=req.session_id,
            source=req.source,
            input=req.text,
            normalized=normalized,
            model_input=prediction.model_input,
            intent=outcome.intent,
            confidence=round(prediction.confidence, 4),
            predicted_intent=prediction.intent,
            top_intents=[IntentScoreOut(intent=s.intent, confidence=round(s.confidence, 4)) for s in prediction.top(3)],
            alternatives=[IntentScoreOut(intent=s.intent, confidence=round(s.confidence, 4)) for s in prediction.ranking[1:3]],
            explanation=[FeatureOut(feature=f.feature, kind=f.kind, weight=f.weight) for f in prediction.explanation],
            entities=outcome.entities,
            missing_entities=outcome.missing,
            thresholds=Thresholds(execute=prefs.execute_threshold, clarify=prefs.clarify_threshold),
            decision=outcome.decision,  # type: ignore[arg-type]
            decision_reason=outcome.reason,
            action=outcome.action,
            response=outcome.response,
            success=outcome.success,
            data=outcome.data,
            context_used=outcome.context_used,
            context=self.contexts.snapshot(ctx),
            notes=outcome.notes,
            pipeline=trace.steps,
            processing_ms=elapsed,
        )
        return response

    # ======================================================== decision from classifier
    def _decide(self, db, ctx, raw, normalized, pred: Prediction, prefs: NovaSettings, trace: Trace) -> Outcome:
        intent, conf = pred.intent, pred.confidence
        execute_t, clarify_t = prefs.execute_threshold, prefs.clarify_threshold

        if conf < clarify_t:
            reason = f"Confidence {conf:.1%} is below the clarification threshold ({clarify_t:.0%}), so Nova won't guess."
            trace.add("confidence", "Confidence evaluation", reason, "warn")
            return Outcome(intent, "UNKNOWN", reason, R.low_confidence_message())
        if intent == "UNKNOWN":
            reason = f"The classifier recognised this as out of scope (UNKNOWN, {conf:.1%})."
            trace.add("confidence", "Confidence evaluation", reason, "warn")
            return Outcome(intent, "UNKNOWN", reason, R.unsupported_message())
        if conf < execute_t:
            reason = (
                f"Confidence {conf:.1%} is between the clarification ({clarify_t:.0%}) and execution ({execute_t:.0%}) "
                f"thresholds, so Nova asks for confirmation before acting."
            )
            trace.add("confidence", "Confidence evaluation", reason, "warn")
            question = R.confirm_question(intent, conf)
            self.contexts.set_pending(ctx, PendingAction(kind="confirm", intent=intent, question=question, original_text=raw, confidence=conf))
            return Outcome(intent, "CONFIRM", reason, question)

        trace.add("confidence", "Confidence evaluation", f"Confidence {conf:.1%} ≥ execution threshold ({execute_t:.0%}).")
        return self._extract_and_execute(db, ctx, intent, raw, normalized, prefs, trace, base_reason=f"Confidence {conf:.1%} ≥ {execute_t:.0%}")

    def _extract_and_execute(self, db, ctx, intent, raw, normalized, prefs, trace, base_reason: str, context_used: str | None = None) -> Outcome:
        ents = extract_entities(intent, normalized, now())
        self._trace_entities(trace, intent, ents)
        if ents.missing:
            slot = ents.missing[0]
            question = R.slot_question(intent, slot, ents.entities, ents.notes)
            self.contexts.set_pending(
                ctx,
                PendingAction(kind="slot", intent=intent, question=question, original_text=raw, entities=ents.entities, missing=ents.missing),
            )
            reason = f"{base_reason}, but the required parameter “{slot}” is missing, so Nova asks for it and keeps the request in context."
            trace.add("decision", "Decision", f"CLARIFY – {reason}", "warn")
            return Outcome(intent, "CLARIFY", reason, question, entities=ents.entities, missing=ents.missing, context_used=context_used, notes=ents.notes)

        reason = f"{base_reason} and all required parameters are present → execute {intent}."
        trace.add("decision", "Decision", f"EXECUTE – {reason}")
        self.contexts.set_pending(ctx, None)
        result = self._run(db, ctx, intent, ents.entities, normalized, prefs, trace)
        return Outcome(
            intent, "EXECUTE", reason, result.message, result.success, ents.entities, [], intent, result.data, context_used, ents.notes
        )

    # =============================================================== pending context
    def _resolve_pending(self, db, ctx: ConversationContext, raw, normalized, pred: Prediction, prefs, trace) -> Outcome | None:
        pending = ctx.pending
        assert pending is not None

        if R.is_cancel(normalized) or (pending.kind == "slot" and R.is_no(normalized)):
            self.contexts.set_pending(ctx, None)
            trace.add("context", "Context resolution", f"User cancelled the pending {pending.intent} request.")
            return Outcome(pending.intent, "CANCELLED", "The user cancelled the pending request.", "Okay, never mind.", True, context_used="cancel_pending")

        if pending.kind == "confirm":
            if R.is_yes(normalized):
                self.contexts.set_pending(ctx, None)
                trace.add("context", "Context resolution", f"User confirmed the {pending.intent} interpretation ({pending.confidence:.1%}).")
                return self._extract_and_execute(
                    db, ctx, pending.intent, pending.original_text, normalize_text(pending.original_text), prefs, trace,
                    base_reason="The user confirmed the predicted intent", context_used="confirmation",
                )
            if R.is_no(normalized):
                self.contexts.set_pending(ctx, None)
                trace.add("context", "Context resolution", f"User rejected the {pending.intent} interpretation.")
                return Outcome(pending.intent, "CANCELLED", "The user rejected the suggested interpretation.",
                               "Okay, I won't do that. What would you like me to do instead?", True, context_used="confirmation_rejected")
            self.contexts.set_pending(ctx, None)
            trace.add("context", "Context resolution", "Pending confirmation dropped – the user said something new.", "skip")
            return None

        # ---- slot filling: re-extract on the original request + the new answer
        before = set(pending.missing)
        combined = f"{normalize_text(pending.original_text)} {normalized}"
        ents = extract_entities(pending.intent, combined, now())
        progress = len(set(ents.missing)) < len(before) or not ents.missing
        confident_other = (
            pred.intent not in (pending.intent, "UNKNOWN") and pred.confidence >= prefs.execute_threshold
        )
        short_answer = len(normalized.split()) <= 6

        if progress and (short_answer or not confident_other):
            filled = sorted(before - set(ents.missing))
            trace.add("context", "Context resolution", f"Filled missing slot(s) {', '.join(filled) or '-'} for pending {pending.intent} using “{normalized}”.")
            self._trace_entities(trace, pending.intent, ents)
            if ents.missing:
                slot = ents.missing[0]
                question = R.slot_question(pending.intent, slot, ents.entities, ents.notes)
                self.contexts.set_pending(ctx, PendingAction(kind="slot", intent=pending.intent, question=question,
                                                             original_text=f"{pending.original_text} {raw}", entities=ents.entities, missing=ents.missing))
                reason = f"Context filled part of the request; “{slot}” is still missing."
                trace.add("decision", "Decision", f"CLARIFY – {reason}", "warn")
                return Outcome(pending.intent, "CLARIFY", reason, question, entities=ents.entities, missing=ents.missing, context_used="slot_filling", notes=ents.notes)
            self.contexts.set_pending(ctx, None)
            reason = f"The answer completed the pending {pending.intent} request → execute."
            trace.add("decision", "Decision", f"EXECUTE – {reason}")
            result = self._run(db, ctx, pending.intent, ents.entities, combined, prefs, trace)
            return Outcome(pending.intent, "EXECUTE", reason, result.message, result.success, ents.entities, [], pending.intent,
                           result.data, "slot_filling", ents.notes)

        if confident_other:
            self.contexts.set_pending(ctx, None)
            trace.add("context", "Context resolution", f"Pending {pending.intent} question abandoned – new confident request ({pred.intent}).", "skip")
            return None

        pending.attempts += 1
        if pending.attempts >= 2:
            self.contexts.set_pending(ctx, None)
            trace.add("context", "Context resolution", "Could not fill the missing information after two attempts; context cleared.", "warn")
            return Outcome(pending.intent, "UNKNOWN", "The answer didn't contain the missing information (twice).",
                           "Sorry, I still didn't get that. Let's start over — what would you like me to do?", context_used="slot_filling_failed")
        trace.add("context", "Context resolution", f"The answer didn't contain the missing “{pending.missing[0]}”; asking again.", "warn")
        return Outcome(pending.intent, "CLARIFY", "The answer didn't contain the missing information.",
                       f"Sorry, I didn't catch that. {pending.question}", entities=pending.entities, missing=pending.missing, context_used="slot_filling_retry")

    # ============================================================ follow-up to last action
    def _resolve_follow_up(self, db, ctx: ConversationContext, normalized, pred: Prediction, prefs, trace) -> Outcome | None:
        last = ctx.last_action
        assert last is not None
        if not _FOLLOW_UP_GUARD.match(normalized):
            trace.add("context", "Context check", f"Recent action {last.intent} in context, but this isn't a follow-up.", "skip")
            return None
        if normalized[0].isdigit() and pred.intent != last.intent and pred.confidence >= prefs.execute_threshold:
            # e.g. "5 times 5" right after a timer is a new calculation, not "make it 5"
            trace.add("context", "Context check", f"Starts with a number but the classifier is confident it's {pred.intent}; not a follow-up.", "skip")
            return None
        cancel = _FOLLOW_UP_CANCEL.match(normalized)
        modify = None if cancel else _FOLLOW_UP_MODIFY.match(normalized)
        if not (cancel or modify):
            return None
        overridden = f"(classifier said {pred.intent} {pred.confidence:.1%}, overridden by context)"

        def done(intent: str, message: str, success: bool, entities: dict[str, Any], data: dict[str, Any] | None = None) -> Outcome:
            reason = f"Follow-up to the previous {last.intent} action {overridden}."
            trace.add("decision", "Decision", f"EXECUTE – {reason}" if success else reason, "ok" if success else "warn")
            return Outcome(intent, "EXECUTE", reason, message, success, entities, [], intent, data or {}, f"follow_up:{last.intent}")

        trace.add("context", "Context resolution", f"Interpreting “{normalized}” as a follow-up to {last.intent}.")
        d = last.data

        if last.intent == "SET_TIMER" and d.get("timer_id"):
            timer = timer_service.get_timer(db, d["timer_id"])
            if timer is None or timer.status != "active":
                return done("SET_TIMER", "That timer has already finished.", False, {})
            if cancel:
                timer_service.cancel_timer(db, timer)
                return done("SET_TIMER", "Okay, I cancelled that timer.", True, {"operation": "cancel"})
            seconds = self._duration_from_follow_up(modify.group("rest"), d.get("duration_seconds", 60))
            if not seconds:
                return None
            timer = timer_service.update_duration(db, timer, seconds)
            self.contexts.set_last_action(ctx, "SET_TIMER", {"timer_id": timer.id, "duration_seconds": seconds})
            return done("SET_TIMER", f"Done — your timer is now {humanize_seconds(seconds)}.", True,
                        {"operation": "modify", "duration_seconds": seconds}, {"timer_id": timer.id})

        if last.intent == "CREATE_REMINDER" and d.get("reminder_id"):
            reminder = reminder_service.get_reminder(db, d["reminder_id"])
            if reminder is None:
                return done("CREATE_REMINDER", "That reminder no longer exists.", False, {})
            if cancel:
                reminder_service.delete_reminder(db, reminder)
                return done("CREATE_REMINDER", "Okay, I deleted that reminder.", True, {"operation": "delete"})
            dt = parse_datetime(modify.group("rest"), now())
            if not dt.when:
                return None
            try:
                reminder_service.reschedule(db, reminder, dt.when)
            except ValueError as exc:
                return done("CREATE_REMINDER", str(exc), False, {})
            from app.core.timeutils import describe_datetime

            return done("CREATE_REMINDER", f"Done — I moved that reminder to {describe_datetime(dt.when, now())}.", True,
                        {"operation": "reschedule", "due_at": dt.when.isoformat()})
        return None

    @staticmethod
    def _duration_from_follow_up(text: str, previous_seconds: int) -> int | None:
        dur = extract_duration(text)
        if dur:
            return dur.seconds
        number = bare_number(text)
        if number is None:
            return None
        # "make it 15" inherits the unit of the original request
        unit = 3600 if previous_seconds >= 3600 and previous_seconds % 3600 == 0 else 60 if previous_seconds >= 60 else 1
        return int(number * unit)

    # ================================================================ helpers
    def _run(self, db, ctx: ConversationContext, intent: str, entities: dict[str, Any], text: str, prefs, trace: Trace) -> ActionResult:
        actx = ActionContext(
            db=db, prefs=prefs, now=now(), text=text, knowledge_base=self.knowledge_base,
            open_browser_on_server=self.open_browser_on_server, last_action=ctx.last_action.data if ctx.last_action else None,
        )
        result = self.registry.execute(intent, entities, actx)
        trace.add("action", "Action execution", f"{intent} → {'success' if result.success else 'failed'}"
                  + (f" ({result.error})" if result.error else ""), "ok" if result.success else "error")
        if result.success and result.context:
            self.contexts.set_last_action(ctx, intent, result.context)
        return result

    @staticmethod
    def _trace_entities(trace: Trace, intent: str, ents: EntityResult) -> None:
        found = ", ".join(f"{k}={v}" for k, v in ents.entities.items()) or "none"
        detail = f"{intent}: {found}" + (f" | missing: {', '.join(ents.missing)}" if ents.missing else "")
        trace.add("entities", "Entity extraction", detail, "warn" if ents.missing else "ok")

# Progress checklist (Definition of Done)

Status as of 2026-11-20. "Verified" means exercised by automated tests and/or a real run of the app
(the API driven over HTTP and the UI driven in Microsoft Edge with Playwright).

| Item | Status | How it was verified |
|---|---|---|
| Backend starts successfully | ✅ | uvicorn start-up; `/api/health` → `ok` |
| Frontend starts successfully | ✅ | `npm run dev`, `npm run build` (type-check passes) |
| ML model is trained | ✅ | `python ml/train_model.py` → 90.4 % test acc., 91.3 % CV |
| Model loads during backend start-up | ✅ | lifespan log + health endpoint; auto-train if missing |
| Predictions work on unseen sentences | ✅ | 35-sentence unseen file 100 %; `test_ml.py` |
| Confidence scores returned | ✅ | API response + inspector |
| Low-confidence requests handled | ✅ | `UNKNOWN` / `CONFIRM` decisions; `test_api.py` |
| Text commands work | ✅ | API + UI walkthrough |
| Voice input works on a supported browser | ⚠️ implemented | Web Speech API hook with error handling; needs a manual check with a real microphone in Chrome/Edge (not possible in headless automation) |
| Nova speaks its responses | ⚠️ implemented | speechSynthesis hook, de-duplicated per message; audio output needs a manual listen |
| Time and date | ✅ | tests + UI |
| Calculator | ✅ | tests (incl. code-injection rejection) + UI |
| Timers | ✅ | tests; UI countdown; completion toast observed in the browser |
| Reminders persist in SQLite | ✅ | tests + UI |
| Focus mode | ✅ | tests + UI |
| Website opening via safe allow-list | ✅ | tests; server-side opening disabled during automated runs |
| AI Decision Inspector shows actual model output | ✅ | UI screenshots; values come from `predict_proba` |
| Conversation history | ✅ | tests + UI (filters, per-row inspector) |
| Analytics from real interactions | ✅ | tests + UI; empty state when no data |
| Settings persist | ✅ | tests + UI (theme switch persisted) |
| Error handling | ✅ | invalid input, offline backend banner, action failures, model missing |
| Tests pass | ✅ | 108 passed |
| README with setup instructions | ✅ | README.md |
| No fake / non-functional UI elements | ✅ | all buttons call real endpoints; charts use stored data |
| Weather | ✅ | Open-Meteo live lookups verified (London, Pune); "not configured" path tested |
| Anthropic / Ollama provider | ⚠️ implemented | provider abstraction + offline fallback tested; live LLM calls not tested (no key / no Ollama) |

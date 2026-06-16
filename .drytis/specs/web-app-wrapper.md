# Task: Wrap Financial AI Advisor in FastAPI Web App

## Goal
Transform the CLI-only Financial AI Advisor into a deployable web application with a chat UI.

## Files to Create
1. `app.py` — FastAPI server with endpoints: GET /, POST /api/ask, GET /api/health
2. `templates/index.html` — Chat UI (financial theme, dark mode)
3. `requirements.txt` — Root-level dependencies
4. `setup.sh` — (replaced by setup script in backend, but document the steps)

## Files to Modify
1. `rag_agent.py` — Lazy-load SentenceTransformer + ChromaDB (crash-safe import)
2. `finbert_agent.py` — Lazy-load tokenizer + model (crash-safe import)
3. `llm_merge_gemini.py` — Cache Gemini LLM instance (singleton)
4. `news_agent.py` — Remove 119 lines of commented-out old code
5. `coordinator_graph.py` — Remove commented old code, add sync wrapper for FastAPI
6. `.gitignore` — Fix merge conflict markers

## Files to Delete
1. `FMP.TEXT` — Contains exposed Alpaca API key (security risk)

## Acceptance Criteria
- [ ] FastAPI server starts without errors on `uvicorn app:app --host 0.0.0.0 --port 8000`
- [ ] GET / returns the chat UI
- [ ] POST /api/ask accepts {"question": "...", "industry": "..."} and returns {"answer": "..."}
- [ ] GET /api/health returns {"status": "ok", "agents": {...}}
- [ ] Models load lazily — no crash on import if models not downloaded
- [ ] Missing API keys result in graceful degradation, not crashes
- [ ] Gemini LLM instance is cached (not recreated per call)
- [ ] No hardcoded secrets or API keys in any source file
- [ ] App responds to curl from localhost
- [ ] Background service runs Uvicorn with production command (not dev mode)

## Tests
- Unit: test router routing logic
- Integration: test /api/health endpoint returns 200
- Integration: test /api/ask returns structured response (mock LLM if no key)
```

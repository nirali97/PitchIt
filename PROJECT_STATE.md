# PROJECT_STATE
Updated: 2026-11-05. Milestone: M1 "Activate & verify AI integration" (user roadmap item 1) — code complete, UNVERIFIED (tests not run, no network/deps in sandbox).

## Exists (code present)
Auth (JWT/pbkdf2), sessions, decision log, 2 cases, rule-based evaluator, LLM abstraction (Groq, cost tracking), stub counterfactual, profile avg, single-file React UI.
## Changed this session
- services/evidence.py: verbatim evidence extraction (replaces fabricated `text[:240]` quote on every dimension).
- services/quant.py: deterministic arithmetic (pct change, margin, break-even, tolerance, case ground truth).
- evaluation.py now uses find_evidence (edited; NOT executed, pydantic unavailable).
## Top weaknesses (priority)
1. Evaluator is keyword matching; scores 3.5/2.5/1.5 on keyword presence. Not reasoning-aware. Needs structured extraction + LLM eval with quote validation (is_verbatim).
2. Quant Lab absent: quant.py exists but no route/UI/answer-grading; no reasoning-vs-number separation.
3. Counterfactual is static boilerplate, not derived from Decision history; no observed-vs-simulated labelling per step.
## Not started
Thinking Lab, Quant Lab UI, Pressure Room personalities/timer, Alembic, Tailwind, frontend tests, deployment config, case state machine/exhibits, adaptive difficulty.
## Known defects
- frontend/package.json uses "latest", lacks @types/react, @types/react-dom; `tsc -b` will likely fail.
- Frontend is one 13-line minified file; needs splitting.
- No ownership/isolation API tests (cross-user session access).
- Env: sandbox has no network; backend deps and node_modules not installed here.
## Next task
Run in an environment with network: `pip install -r requirements.txt && pytest`, then fix whatever fails; then replace evaluator (weakness 1).

## M1 changes (AI integration)
- routes.py: user's updated version installed (strict 502 on Groq failure) + sanitized error, logging, rollback so failed turn isn't half-saved; GET /api/ai/status[?probe=true]; GET /api/usage.
- llm/base.py: failed provider calls now recorded (task ':failed'). llm/factory.py: shared get_llm() (was new HTTP client per request). llm/groq.py: retry 429/5xx/network x3.
- tests/test_ai_integration.py (8 tests, fake provider + httpx MockTransport) — NOT RUN.
## User roadmap (order): 1 AI integration -> 2 case library (25-30) -> 3 adaptive interviewer -> 4 rebuild evaluation -> 5 Thinking/Quant Lab -> 6 My Intelligence
## Open items for M1 sign-off
- Run pytest; run live probe with real key: GET /api/ai/status?probe=true.
- Set LLM_PRICING_JSON (cost is 0 otherwise). Verify current Groq model ids in .env.
- case_facts all returned on every turn (spoils progressive reveal; fix in M3).

## Session 3 (user reported failing tests; pytest output not provided)
- Root-cause fix (db.py): in-memory `sqlite://` lacked StaticPool, so TestClient worker threads saw an empty DB ("no such table"). Most likely cause of the failures; UNVERIFIED until pytest is re-run.
- Phase 2 (case library): cases.py rebuilt, 13 cases (6 profitability w/ computed numbers, break-even, pricing, sizing, M&A, ops, growth, market entry). Target 25-30 NOT reached.
- Phase 3 (interviewer): progressive fact reveal (services/interviewer.py), state["revealed"], LLM gets only revealed + NEW facts, stage-aware non-repeating fallback questions, frontend refreshes facts per turn. API no longer leaks gated facts/exhibits.
- Tests: tests/test_cases_interviewer.py 5/5 PASS (run in sandbox); test_quant_evidence 7/7 PASS; test_core (+1 reveal test) and test_ai_integration NOT RUN here.
## Next: re-run pytest; live Groq probe; rebuild evaluator (roadmap 4); Thinking/Quant Lab (5); My Intelligence (6); 12-17 more cases.

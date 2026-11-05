# TEST_STATUS (2026-11-05)
| Suite | Result | Notes |
|---|---|---|
| tests/test_quant_evidence.py (stdlib unittest) | PASS 7/7 | run: `python -m unittest tests.test_quant_evidence` |
| python -m compileall backend | PASS | syntax only |
| tests/test_core.py (pytest, API flow) | NOT RUN | fastapi/sqlalchemy/pydantic not installable offline |
| evaluation.py after evidence change | NOT RUN | needs pydantic |
| Frontend tsc/vite build | NOT RUN | no node_modules, no network |
| Regression | UNVERIFIED | cannot be claimed |
| tests/test_ai_integration.py (pytest) | NOT RUN (written) | needs fastapi/pydantic/httpx; 8 tests |
| Live Groq call | NOT VERIFIED | needs your GROQ_API_KEY; use /api/ai/status?probe=true |

## 2026-11-05 user run: pytest collected 0 items / 3 errors (ModuleNotFoundError: app). Cause: no pythonpath config. Fix: backend/pytest.ini + conftest.py (also forces in-memory DB and empty GROQ_API_KEY). Re-run needed.

## Session 3
| tests/test_cases_interviewer.py | PASS 5/5 (sandbox) |
| tests/test_quant_evidence.py | PASS 7/7 (sandbox) |
| tests/test_core.py (+reveal test), tests/test_ai_integration.py | NOT RUN - re-run `pytest -v` and send output |

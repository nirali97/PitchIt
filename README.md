# PitchIt

**An adaptive consulting reasoning and practice platform.** PitchIt is designed to coach the thinking behind a case answer, not simply grade the final answer.

This repository now contains a runnable full-stack foundation: a React/Vite frontend, FastAPI backend, authentication, persistent practice sessions and decisions, case prompts, an adaptive interviewer (Groq when configured, deterministic fallback otherwise), a transparent seven-dimension baseline diagnostic, learner profile, and counterfactual practice paths.

> Important: the current evaluator is an early rule-based diagnostic with low confidence. It is not a validated consulting-interview score or hiring prediction. The counterfactual feature currently generates structured alternative practice paths; it does not simulate a full causal business model yet.

## Project structure

```text
pitchit/
├── backend/
│   ├── app/
│   │   ├── api/                 # API routes and DB dependency
│   │   ├── llm/                 # Provider abstraction, Groq, cost/token logging
│   │   ├── services/            # Case library and baseline evaluation
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── security.py
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
└── frontend/
    ├── src/
    ├── .env.example
    ├── package.json
    └── vite.config.ts
```

## Run locally

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Set a long random `JWT_SECRET` in `backend/.env`. For Groq-powered adaptive interviewer questions, add your `GROQ_API_KEY`. Without a key, the app uses a deterministic interviewer fallback and remains usable.

```bash
uvicorn app.main:app --reload
```

API: http://localhost:8000  
Swagger docs: http://localhost:8000/docs

SQLite is used by default. For deployment, set `DATABASE_URL` to a PostgreSQL connection URL. Tables are currently initialized automatically for the MVP; Alembic migrations should be added before production schema changes.

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173. Set `VITE_API_URL` if the backend is hosted somewhere other than `http://localhost:8000`.

## Implemented API

- `POST /api/auth/register` — create account
- `POST /api/auth/login` — sign in
- `GET /api/auth/me` — current user
- `GET /api/cases` — available cases
- `POST /api/sessions` — start a practice session
- `GET /api/sessions` — list session history
- `GET /api/sessions/{id}` — session and decision history
- `POST /api/sessions/{id}/turn` — submit answer and receive interviewer follow-up
- `POST /api/sessions/{id}/decisions` — add structured decision event
- `POST /api/sessions/{id}/evaluate` — evaluate seven dimensions
- `GET /api/sessions/{id}/counterfactual` — inspect alternative reasoning paths
- `GET /api/profile` — aggregate learner profile
- `GET /health` — health check

All practice endpoints require `Authorization: Bearer <token>`.

## Tests

```bash
cd backend
JWT_SECRET=test-secret-long-enough-for-local-tests-123456789 DATABASE_URL=sqlite:////tmp/pitchit_test.db python -m pytest -q
```

## Current scope and next engineering milestones

1. Replace the baseline evaluator with an evidence-grounded structured evaluation rubric and a manually reviewed benchmark set.
2. Build a real case state machine with staged exhibits, validated numeric facts, and branching case logic.
3. Implement issue-tree extraction and structured hypothesis/evidence tracking.
4. Upgrade counterfactuals to compare explicit alternative decisions against case constraints.
5. Add Thinking Lab and Quant Lab exercise engines.
6. Add proper Alembic migrations, refresh-token/session revocation, rate limiting, and production security review.
7. Add voice interaction and richer analytics after the text experience is reliable.

## Security notes

- Never commit `.env` or API keys.
- Change `JWT_SECRET` to a strong random value before deployment.
- Configure `CORS_ORIGINS` to the exact deployed frontend origin(s).
- Use HTTPS and managed PostgreSQL in production.
- Add rate limits and account verification before public launch.

# PitchIt

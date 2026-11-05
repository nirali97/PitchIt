import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from ..api.deps import get_db
from ..models import User, Session as PracticeSession, Decision, DimensionScore, LLMCall
from ..schemas import RegisterIn, LoginIn, SessionCreate, TurnIn, DecisionIn
from ..security import (
    hash_password,
    verify_password,
    create_token,
    current_user
)
from ..services.cases import CASES, public_case, initial_indices
from ..services.interviewer import update_reveals, fact_texts, stage_question
from ..services.evaluation import evaluate_text
from ..config import get_settings
from ..main_state import SessionLocal
from ..llm.factory import get_llm
from ..llm.base import LLMRequest, LLMError


router = APIRouter(prefix="/api")
logger = logging.getLogger("pitchit.api")


# ============================================================
# AUTHENTICATION
# ============================================================

@router.post("/auth/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):

    if db.scalar(
        select(User).where(User.email == data.email.lower())
    ):
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists"
        )

    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        display_name=data.display_name,
        experience_level=data.experience_level
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "access_token": create_token(user.id),
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "experience_level": user.experience_level
        }
    }


@router.post("/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):

    user = db.scalar(
        select(User).where(User.email == data.email.lower())
    )

    if not user or not verify_password(
        data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    return {
        "access_token": create_token(user.id),
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "experience_level": user.experience_level
        }
    }


@router.get("/auth/me")
def me(user: User = Depends(current_user)):

    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "experience_level": user.experience_level
    }


# ============================================================
# CASE LIBRARY
# ============================================================

@router.get("/cases")
def list_cases(user: User = Depends(current_user)):

    return [
        {
            "id": key,
            "title": value["title"],
            "type": value["type"],
            "difficulty": value["difficulty"],
            "industry": value["industry"],
            "prompt": value["prompt"],
            "opening_question": value["opening_question"]
        }
        for key, value in CASES.items()
    ]


# ============================================================
# PRACTICE SESSIONS
# ============================================================

@router.post("/sessions")
def create_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):

    if data.module == "case" and data.case_ref not in CASES:
        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    case = CASES.get(data.case_ref)
    revealed = initial_indices(case) if case else []

    s = PracticeSession(
        user_id=user.id,
        module=data.module,
        case_ref=data.case_ref,
        state={
            "turn": 0,
            "transcript": [],
            "status": "active",
            "revealed": revealed
        }
    )

    db.add(s)
    db.commit()
    db.refresh(s)

    return {
        "id": s.id,
        "module": s.module,
        "case": public_case(case, revealed) if case else None,
        "opening_question": (
            case["opening_question"]
            if case
            else "What problem would you like to work through?"
        )
    }


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):

    rows = db.scalars(
        select(PracticeSession)
        .where(PracticeSession.user_id == user.id)
        .order_by(PracticeSession.created_at.desc())
        .limit(50)
    ).all()

    return [
        {
            "id": s.id,
            "module": s.module,
            "case_ref": s.case_ref,
            "status": s.status,
            "created_at": s.created_at.isoformat()
        }
        for s in rows
    ]


def owned_session(
    session_id: int,
    db: Session,
    user: User
):

    s = db.get(PracticeSession, session_id)

    if not s or s.user_id != user.id:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return s


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):

    s = owned_session(session_id, db, user)

    decisions = db.scalars(
        select(Decision)
        .where(Decision.session_id == s.id)
        .order_by(Decision.seq)
    ).all()

    return {
        "id": s.id,
        "module": s.module,
        "case_ref": s.case_ref,
        "status": s.status,
        "state": s.state,
        "decisions": [
            {
                "id": d.id,
                "seq": d.seq,
                "kind": d.kind,
                "content": d.content,
                "payload": d.payload,
                "parent_id": d.parent_id
            }
            for d in decisions
        ]
    }


# ============================================================
# DECISION RECORDING
# ============================================================

@router.post("/sessions/{session_id}/decisions")
def add_decision(
    session_id: int,
    data: DecisionIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):

    s = owned_session(session_id, db, user)

    if data.parent_id and not db.scalar(
        select(Decision).where(
            Decision.id == data.parent_id,
            Decision.session_id == s.id
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Parent decision must belong to this session"
        )

    seq = (
        db.scalar(
            select(func.max(Decision.seq))
            .where(Decision.session_id == s.id)
        ) or 0
    ) + 1

    d = Decision(
        session_id=s.id,
        seq=seq,
        kind=data.kind,
        content=data.content,
        payload=data.payload,
        parent_id=data.parent_id
    )

    db.add(d)
    db.commit()
    db.refresh(d)

    return {
        "id": d.id,
        "seq": d.seq,
        "kind": d.kind,
        "content": d.content
    }


# ============================================================
# ADAPTIVE AI INTERVIEWER
# ============================================================

@router.post("/sessions/{session_id}/turn")
def submit_turn(
    session_id: int,
    data: TurnIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):

    s = owned_session(session_id, db, user)

    if s.status != "active":
        raise HTTPException(
            status_code=409,
            detail="This session is already completed"
        )

    seq = (
        db.scalar(
            select(func.max(Decision.seq))
            .where(Decision.session_id == s.id)
        ) or 0
    ) + 1

    d = Decision(
        session_id=s.id,
        seq=seq,
        kind="decision",
        content=data.message,
        payload={"source": "candidate_turn"}
    )

    db.add(d)

    state = dict(s.state or {})
    transcript = list(state.get("transcript", []))

    transcript.append({
        "role": "candidate",
        "content": data.message
    })

    state["transcript"] = transcript
    state["turn"] = state.get("turn", 0) + 1

    case = CASES.get(s.case_ref, {})
    settings = get_settings()

    if case:
        revealed, newly = update_reveals(
            case, data.message,
            state.get("revealed") or initial_indices(case)
        )
    else:
        revealed, newly = [], []
    state["revealed"] = revealed
    known_facts = fact_texts(case, revealed)
    new_facts = fact_texts(case, newly)

    reply = None
    mode = "rule_based_interviewer"

    # --------------------------------------------------------
    # GROQ AI INTERVIEWER
    # --------------------------------------------------------

    if settings.groq_api_key:

        try:

            llm = get_llm(settings, SessionLocal)

            # Include recent conversation history.
            prior = "\n".join(
                f"{message['role']}: {message['content']}"
                for message in transcript[-10:]
            )

            result = llm.run(
                LLMRequest(
                    task="adaptive_interviewer",
                    tier="strong",
                    temperature=0.4,
                    max_tokens=1000,
                    use_cache=False,

                    system=(
                        "You are PitchIt, an intelligent management "
                        "consulting case interviewer.\n\n"

                        "Your role is to simulate a realistic "
                        "consulting case interview.\n\n"

                        "INTERVIEW RULES:\n"
                        "1. Understand the candidate's latest answer "
                        "before responding.\n"
                        "2. Remember the previous conversation.\n"
                        "3. Never repeat a question already asked "
                        "unless clarification is genuinely necessary.\n"
                        "4. Challenge weak assumptions and unsupported "
                        "conclusions.\n"
                        "5. Ask for calculations when quantitative "
                        "reasoning is appropriate.\n"
                        "6. Use ONLY the facts under AVAILABLE CASE FACTS. "
                        "Never invent numbers. If NEW FACTS TO SHARE is "
                        "non-empty, state those facts plainly first, then "
                        "ask your question.\n"
                        "7. If the candidate changes their hypothesis, "
                        "recognize and respond to that change.\n"
                        "8. Do not immediately reveal the solution.\n"
                        "9. Do not unnecessarily praise every answer.\n"
                        "10. Ask exactly ONE concise follow-up question.\n\n"

                        "Your tone should be professional, probing, "
                        "realistic and intellectually challenging.\n\n"

                        "You are an interviewer, not a tutor. "
                        "Do not give away the answer."
                    ),

                    user=(
                        f"CASE TITLE:\n"
                        f"{case.get('title', 'Practice case')}\n\n"

                        f"CASE BRIEF:\n"
                        f"{case.get('prompt', '')}\n\n"

                        f"AVAILABLE CASE FACTS:\n"
                        f"{known_facts}\n\n"

                        f"NEW FACTS TO SHARE:\n"
                        f"{new_facts}\n\n"

                        f"RECENT CONVERSATION:\n"
                        f"{prior}\n\n"

                        f"LATEST CANDIDATE ANSWER:\n"
                        f"{data.message}\n\n"

                        "Based on the complete context, ask the "
                        "single most useful next interviewer question."
                    ),

                    user_id=user.id
                )
            )

            reply = result.text.strip()

            if not reply:
                raise LLMError("Groq returned an empty response")

            mode = "groq"

        except Exception as exc:

            # Full detail goes to server logs; the client gets a safe message.
            # Nothing was committed, so the candidate's turn is not recorded
            # and can simply be re-sent.
            logger.exception("AI interviewer failed (session %s)", s.id)
            db.rollback()

            raise HTTPException(
                status_code=502,
                detail=(
                    f"The AI interviewer is temporarily unavailable "
                    f"({type(exc).__name__}). Your answer was not "
                    f"recorded; please try sending it again."
                )
            ) from exc

    # --------------------------------------------------------
    # RULE-BASED FALLBACK
    # Used only when no Groq API key is configured.
    # --------------------------------------------------------

    else:

        candidate_msgs = [m["content"] for m in transcript if m["role"] == "candidate"]
        prior_qs = [m["content"].split("\n")[-1] for m in transcript if m["role"] == "interviewer"]
        question = stage_question(candidate_msgs, prior_qs)
        reply = (
            "Here is the data you asked for: " + " ".join(new_facts) + "\n" + question
            if new_facts else question
        )

    # --------------------------------------------------------
    # SAVE INTERVIEWER RESPONSE
    # --------------------------------------------------------

    transcript.append({
        "role": "interviewer",
        "content": reply
    })

    state["transcript"] = transcript
    s.state = state

    db.commit()
    db.refresh(d)

    return {
        "decision_id": d.id,
        "turn": state["turn"],
        "reply": reply,
        "mode": mode,
        "case_facts": known_facts,
        "new_facts": new_facts
    }


# ============================================================
# SESSION EVALUATION
# ============================================================

@router.post("/sessions/{session_id}/evaluate")
def evaluate_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):

    s = owned_session(session_id, db, user)

    decisions = db.scalars(
        select(Decision)
        .where(Decision.session_id == s.id)
        .order_by(Decision.seq)
    ).all()

    candidate_text = "\n".join(
        d.content
        for d in decisions
        if (
            d.payload.get("source") == "candidate_turn"
            or d.kind in (
                "assumption",
                "hypothesis",
                "question",
                "evidence",
                "decision",
                "revision",
                "conclusion"
            )
        )
    )

    if not candidate_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Add some reasoning before requesting an evaluation"
        )

    result = evaluate_text(candidate_text)

    for item in result.dimensions:

        db.add(
            DimensionScore(
                session_id=s.id,
                user_id=user.id,
                dimension=item.dimension,
                score=item.score,
                confidence=item.confidence,
                rationale=item.rationale,
                evidence=item.evidence,
                weakness=item.weakness,
                improvement=item.improvement,
                rubric_version="baseline-v1"
            )
        )

    s.status = "completed"
    db.commit()

    return result.model_dump()


# ============================================================
# COUNTERFACTUAL ANALYSIS
# ============================================================

@router.get("/sessions/{session_id}/counterfactual")
def counterfactual(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):

    s = owned_session(session_id, db, user)

    decisions = db.scalars(
        select(Decision)
        .where(Decision.session_id == s.id)
        .order_by(Decision.seq)
    ).all()

    if not decisions:
        raise HTTPException(
            status_code=400,
            detail="No decisions recorded yet"
        )

    return {
        "session_id": s.id,
        "notice": (
            "These are practice alternatives, not factual predictions."
        ),

        "actual_path": [
            {
                "seq": d.seq,
                "kind": d.kind,
                "content": d.content
            }
            for d in decisions
        ],

        "alternative_paths": [
            {
                "title": "Test the opposite hypothesis",
                "steps": [
                    "State an alternative explanation.",
                    "Identify the evidence that would distinguish "
                    "the explanations.",
                    "Update the recommendation only after "
                    "comparing the evidence."
                ]
            },
            {
                "title": "Prioritize by impact",
                "steps": [
                    "Estimate the size of each driver.",
                    "Rank drivers by likely contribution to the problem.",
                    "Investigate the largest and most uncertain "
                    "driver first."
                ]
            }
        ]
    }


# ============================================================
# USER PERFORMANCE PROFILE
# ============================================================

@router.get("/profile")
def profile(
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):

    rows = db.execute(
        select(
            DimensionScore.dimension,
            func.avg(DimensionScore.score),
            func.count(DimensionScore.id)
        )
        .where(DimensionScore.user_id == user.id)
        .group_by(DimensionScore.dimension)
    ).all()

    sessions = (
        db.scalar(
            select(func.count(PracticeSession.id))
            .where(PracticeSession.user_id == user.id)
        ) or 0
    )

    return {
        "sessions": sessions,

        "dimensions": [
            {
                "dimension": row[0],
                "average_score": round(float(row[1]), 2),
                "observations": row[2]
            }
            for row in rows
        ],

        "note": (
            "Scores are preliminary baseline diagnostics. "
            "They are not validated hiring predictions."
        )
    }


# ============================================================
# AI INTEGRATION: STATUS PROBE + TOKEN USAGE
# ============================================================

@router.get("/ai/status")
def ai_status(probe: bool = False, user: User = Depends(current_user)):
    """Config summary. With ?probe=true makes one tiny live call (~10 tokens)."""
    settings = get_settings()
    info = {
        "provider": settings.llm_provider,
        "configured": bool(settings.groq_api_key),
        "models": {
            "cheap": settings.llm_model_cheap,
            "strong": settings.llm_model_strong,
        },
        "pricing_configured": bool(settings.pricing),
    }
    if probe:
        if not settings.groq_api_key:
            info["probe"] = {"ok": False, "error": "GROQ_API_KEY is not set"}
        else:
            try:
                r = get_llm(settings, SessionLocal).run(LLMRequest(
                    task="ai_probe", tier="cheap", system="Reply with the single word: ok",
                    user="ping", max_tokens=5, use_cache=False, user_id=user.id))
                info["probe"] = {
                    "ok": True, "model": r.model, "latency_ms": r.latency_ms,
                    "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
                }
            except Exception as exc:
                logger.warning("AI probe failed: %s", exc)
                info["probe"] = {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    return info


@router.get("/usage")
def usage(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Token, latency and cost totals for the current user's LLM calls."""
    rows = db.execute(
        select(
            LLMCall.task,
            func.count(LLMCall.id),
            func.coalesce(func.sum(LLMCall.input_tokens), 0),
            func.coalesce(func.sum(LLMCall.output_tokens), 0),
            func.coalesce(func.sum(LLMCall.cost_usd), 0.0),
            func.coalesce(func.avg(LLMCall.latency_ms), 0.0),
        ).where(LLMCall.user_id == user.id).group_by(LLMCall.task)
    ).all()
    by_task = [
        {"task": r[0], "calls": r[1], "input_tokens": int(r[2]), "output_tokens": int(r[3]),
         "cost_usd": round(float(r[4]), 6), "avg_latency_ms": round(float(r[5]))}
        for r in rows
    ]
    return {
        "by_task": by_task,
        "totals": {
            "calls": sum(t["calls"] for t in by_task),
            "failed_calls": sum(t["calls"] for t in by_task if t["task"].endswith(":failed")),
            "input_tokens": sum(t["input_tokens"] for t in by_task),
            "output_tokens": sum(t["output_tokens"] for t in by_task),
            "cost_usd": round(sum(t["cost_usd"] for t in by_task), 6),
        },
        "note": "cost_usd is 0 until LLM_PRICING_JSON is set with your model prices ($ per 1M tokens: [in, out]).",
    }

from sqlalchemy.orm import sessionmaker
from ..config import Settings
from ..models import LLMCall
from .base import LLMError, LLMService
from .groq import GroqProvider

_llm: LLMService | None = None


def make_recorder(session_factory: sessionmaker):
    def record(row: dict):
        with session_factory() as db:
            db.add(LLMCall(**row))
            db.commit()
    return record


def build_llm(settings: Settings, session_factory: sessionmaker) -> LLMService:
    if settings.llm_provider == "groq":
        provider = GroqProvider(settings.groq_api_key)
    else:
        raise LLMError(f"unsupported provider {settings.llm_provider}")
    return LLMService(provider, {"cheap": settings.llm_model_cheap, "strong": settings.llm_model_strong},
                      settings.pricing, make_recorder(session_factory))


def get_llm(settings: Settings, session_factory: sessionmaker) -> LLMService:
    """One shared service per process: reuses the HTTP client and response cache."""
    global _llm
    if _llm is None:
        _llm = build_llm(settings, session_factory)
    return _llm


def reset_llm() -> None:
    global _llm
    _llm = None

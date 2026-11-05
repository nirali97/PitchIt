from .config import get_settings
from .db import make_engine, make_session_factory
settings = get_settings()
engine = make_engine(settings.database_url)
SessionLocal = make_session_factory(engine)

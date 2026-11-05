from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True}
    if url.startswith("sqlite") and (url in ("sqlite://", "sqlite:///") or ":memory:" in url):
        from sqlalchemy.pool import StaticPool
        kw["poolclass"] = StaticPool
    return create_engine(url, **kw)


def make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
_is_memory_sqlite = _is_sqlite and ":memory:" in settings.database_url

_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_engine_kwargs: dict = {"connect_args": _connect_args}
if _is_memory_sqlite:
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    from flask import current_app, g

    if "db" not in g:
        override = current_app.config.get("DB_SESSION")
        g.db = override if override is not None else SessionLocal()
    return g.db

"""Tenant-bound SQLAlchemy sessions for the assessment v2 database."""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.security import CurrentUser


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def _create_assessment_engine(url: str) -> Engine:
    engine = create_engine(url, future=True)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


@lru_cache(maxsize=4)
def get_assessment_engine(database_url: str | None = None):
    url = database_url or get_settings().assessment_database_url
    return _create_assessment_engine(url)


@lru_cache(maxsize=4)
def get_assessment_session_factory(database_url: str | None = None):
    return sessionmaker(
        bind=get_assessment_engine(database_url),
        class_=Session,
        expire_on_commit=False,
    )


@contextmanager
def assessment_session_for(user: CurrentUser, database_url: str | None = None) -> Iterator[Session]:
    """Yield one transaction with PostgreSQL tenant context set locally."""

    session = get_assessment_session_factory(database_url)()
    try:
        if session.bind is not None and session.bind.dialect.name == "postgresql":
            session.execute(
                text("SELECT set_config('app.current_organization_id', :organization_id, true)"),
                {"organization_id": user.organization_id},
            )
            session.execute(
                text("SELECT set_config('app.current_user_id', :user_id, true)"),
                {"user_id": user.user_id},
            )
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()

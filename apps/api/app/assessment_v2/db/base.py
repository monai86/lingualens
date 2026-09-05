"""SQLAlchemy metadata for the isolated assessment v2 database."""

from sqlalchemy.orm import DeclarativeBase


class AssessmentBase(DeclarativeBase):
    """Base class deliberately independent from the legacy v1 metadata."""


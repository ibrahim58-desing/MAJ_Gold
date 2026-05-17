"""
Base service — shared session management for all services.
"""
from contextlib import contextmanager
from database.models.base import SessionLocal


class BaseService:
    """Mixin providing a get_session() context manager."""

    @staticmethod
    @contextmanager
    def get_session():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def new_session():
        """Return a raw session (caller must commit/close)."""
        return SessionLocal()

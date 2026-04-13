from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from database import SessionLocal, engine, ping_database, set_audit_user_on_session

__all__ = [
    "engine",
    "SessionLocal",
    "ping_database",
    "set_audit_user_on_session",
    "get_db",
]


def get_db(request: Request) -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        login = getattr(request.state, "audit_user", None)
        set_audit_user_on_session(db, login)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

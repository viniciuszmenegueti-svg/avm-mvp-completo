from collections.abc import Generator

from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal


def get_database_session() -> Generator[
    Session,
    None,
    None,
]:
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()

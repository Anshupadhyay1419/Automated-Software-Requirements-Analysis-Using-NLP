"""Connects SQLAlchemy to the SQLite database file."""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

if DATABASE_URL.startswith("sqlite:///"):
    Path(DATABASE_URL.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)

# The API and the background analysis use different threads, so SQLite must allow that.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@event.listens_for(engine, "connect")
def turn_on_foreign_keys(connection, _record):
    """SQLite ignores foreign keys unless asked. We need them so that deleting a
    project also deletes its documents, requirements, issues and stories."""
    connection.execute("PRAGMA foreign_keys=ON")


class Base(DeclarativeBase):
    pass


def create_tables():
    from . import models  # noqa: F401  (registers the tables on Base)
    Base.metadata.create_all(engine)


def get_db():
    """Gives each API request its own database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

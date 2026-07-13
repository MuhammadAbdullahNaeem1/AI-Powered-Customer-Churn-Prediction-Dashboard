"""SQLAlchemy engine, session factory, and Base."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import DATABASE_URL  # noqa: E402

# check_same_thread=False lets APScheduler's background thread share the engine.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Safe to call repeatedly."""
    import db.models  # noqa: F401  (register models on Base)

    Base.metadata.create_all(bind=engine)

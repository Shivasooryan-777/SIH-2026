"""
Database Connection & Session Factory
=====================================
Initializes SQLAlchemy engine and session factory for Neon serverless Postgres.
Uses pool_pre_ping=True to gracefully handle Neon's serverless idle timeouts.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.config import get_database_url

DATABASE_URL = get_database_url()

# pool_pre_ping ensures connections checked out from the pool are verified alive,
# which is essential for serverless Postgres (Neon) auto-sleep behavior.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a SQLAlchemy database session.
    Closes the session cleanly upon request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
Application Configuration Module
================================
Safely loads environment variables from .env without exposing credentials.
Database: Neon (serverless Postgres)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Absolute path resolution to repository root
REPO_ROOT = Path(__file__).resolve().parents[2]
DOTENV_PATH = REPO_ROOT / ".env"

if DOTENV_PATH.exists():
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    load_dotenv()


def get_database_url() -> str:
    """
    Retrieve and normalize DATABASE_URL for SQLAlchemy connection to Neon Postgres.

    Note:
    - Normalizes legacy 'postgres://' prefix to 'postgresql://'.
    - Never prints, logs, or returns this string to public endpoints.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Please configure it in .env (without committing .env)."
        )

    # SQLAlchemy 1.4/2.0 requires postgresql:// instead of postgres://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url

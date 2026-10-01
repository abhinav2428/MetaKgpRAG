"""
backend/config.py
-----------------
Central application configuration loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Database ──────────────────────────────────────────────────────────────────
# Explicitly use psycopg2 driver (SQLAlchemy 2.x defaults to psycopg3 otherwise)
_raw_db_url = os.getenv(
    "DATABASE_URL",
    "postgresql://graphmind:graphmind@localhost:5432/graphmind"
)
# Normalise Railway/Render style postgres:// → postgresql+psycopg2://
if _raw_db_url.startswith("postgres://"):
    _raw_db_url = _raw_db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif _raw_db_url.startswith("postgresql://") and "+" not in _raw_db_url.split("://")[0]:
    _raw_db_url = _raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
DATABASE_URL: str = _raw_db_url

# ── JWT Auth ──────────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-please")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

# ── Google OAuth ──────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI: str = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
)

# ── App ───────────────────────────────────────────────────────────────────────
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ===== DATABASE SETUP (FINAL - PRODUCTION READY) =====

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# 🔥 Get DATABASE_URL from Render ENV
DATABASE_URL = os.getenv("DATABASE_URL")

# 🔁 Fallback (local testing only)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./aimant.db"

# 🔥 Fix for Render Postgres (VERY IMPORTANT)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 🔥 Engine setup
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# 🔥 Session setup
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 🔥 Base model
Base = declarative_base()

# 🔥 Dependency (FastAPI use karega)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

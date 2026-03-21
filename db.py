# ===============================
# DATABASE SETUP (FINAL - STABLE)
# ===============================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# ===============================
# GET DATABASE URL (ENV)
# ===============================
DATABASE_URL = os.getenv("DATABASE_URL")

# ===============================
# FALLBACK (LOCAL SQLITE)
# ===============================
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./aimant.db"

# ===============================
# FIX POSTGRES (RENDER ISSUE)
# ===============================
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ===============================
# ENGINE CONFIG
# ===============================
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

# ===============================
# SESSION
# ===============================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ===============================
# BASE (MODELS KE LIYE)
# ===============================
Base = declarative_base()

# ===============================
# DEPENDENCY (FASTAPI USE)
# ===============================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

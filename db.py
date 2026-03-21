# ===== DATABASE SETUP (FINAL - NO ERROR) =====

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Get DATABASE_URL from Render
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback (local)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./aimant.db"

# Fix postgres URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base (IMPORTANT)
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

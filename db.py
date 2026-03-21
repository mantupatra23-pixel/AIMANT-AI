# ===== DATABASE SETUP (SAFE & WORKING) =====

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 🔥 SIMPLE DATABASE (NO ERROR)
DATABASE_URL = "sqlite:///./aimant.db"

# engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# base
Base = declarative_base()

# dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

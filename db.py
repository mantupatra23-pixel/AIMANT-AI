from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# 🔥 GET DATABASE URL FROM RENDER ENV
DATABASE_URL = os.getenv("DATABASE_URL")

# fallback (local testing only)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./aimant.db"

# 🔥 fix for postgres (important)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 🔥 engine setup
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# 🔥 session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 🔥 base
Base = declarative_base()

# 🔥 dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

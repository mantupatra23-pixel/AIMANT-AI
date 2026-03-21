# ===============================
# MODELS (FINAL)
# ===============================

from sqlalchemy import Column, Integer, String
from db import Base

# ===============================
# USER TABLE
# ===============================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, unique=True, index=True, nullable=False)

    password = Column(String, nullable=False)

    credits = Column(Integer, default=20)

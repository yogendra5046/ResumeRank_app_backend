from sqlalchemy import Column, String, Integer, DateTime, JSON
from datetime import datetime
from src.infrastructure.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    
    # Profile Fields
    bio = Column(String, default="")
    target_salary = Column(String, default="")
    work_preference = Column(String, default="")
    experience = Column(JSON, default=list) # List of dicts
    education = Column(JSON, default=list)  # List of dicts
    
    created_at = Column(DateTime, default=datetime.utcnow)

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from datetime import datetime
from src.infrastructure.database import Base

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company_name = Column(String)
    job_title = Column(String)
    applied_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String)
    notes = Column(String, default="")

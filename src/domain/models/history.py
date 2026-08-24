from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from datetime import datetime
from src.infrastructure.database import Base

class HistoryItem(Base):
    __tablename__ = "history_items"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    file_name = Column(String)
    date = Column(DateTime, default=datetime.utcnow)
    score = Column(Integer)
    percentile = Column(Integer)
    missing_keywords = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    full_result_json = Column(String, nullable=True)

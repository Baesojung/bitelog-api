from sqlalchemy import Column, Integer, String, DateTime, Text, func
from app.db.session import Base

class FailedLog(Base):
    __tablename__ = "failed_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, default=1, index=True)
    raw_text = Column(Text, nullable=False)
    error_message = Column(Text) # Error details from AI or System
    created_at = Column(DateTime(timezone=True), server_default=func.now())

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.sql import func
from db import Base

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True)
    user_id = Column(Integer, nullable=False)
    type = Column(String, nullable=False)  # "sell" или "buy"
    data = Column(Text, nullable=False)  # JSON
    invited = Column(Boolean, default=False)
    rejected_all = Column(Boolean, default=False)
    status = Column(String, default="pending")  # pending, published, rejected
    created_at = Column(DateTime, server_default=func.now())
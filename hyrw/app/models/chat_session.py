from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_session"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    nlsql_task_id = Column(Integer, ForeignKey("nlsql_task_config.id", ondelete="CASCADE"), nullable=False)
    session_title = Column(String(255), comment="会话标题")
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    nlsql_task = relationship("NlsqlTaskConfig")
    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")

    class Config:
        from_attributes = True

from sqlalchemy import Column, Integer, Text, DateTime, Boolean, ForeignKey, text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversation"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    session_id = Column(Integer, ForeignKey("chat_session.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False, comment="问题")
    answer = Column(Text, comment="回答")
    description = Column(Text, comment="描述")
    nlsql_task_id = Column(Integer, ForeignKey("nlsql_task_config.id", ondelete="CASCADE"), nullable=False)
    is_right = Column(Boolean, comment="是否正确")
    sql_generated = Column(Text, comment="生成的SQL")
    sql_result = Column(Text, comment="SQL执行返回数据(JSON)")
    selected_tables = Column(Text, comment="选表代理返回的表列表(JSON)")
    query_context = Column(Text, comment="查询上下文(JSON)")
    column_patch = Column(Text, comment="列补丁(JSON)")
    feedback = Column(Text, comment="反馈信息")
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    session = relationship("ChatSession", back_populates="conversations")
    nlsql_task = relationship("NlsqlTaskConfig")

    class Config:
        from_attributes = True

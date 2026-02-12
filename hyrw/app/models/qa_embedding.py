from sqlalchemy import Column, Integer, Text, DateTime, Boolean, ForeignKey, text
from sqlalchemy.orm import relationship
from app.core.database import Base


class QaEmbedding(Base):
    __tablename__ = "qa_embedding"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    question = Column(Text, nullable=False, comment="问题")
    nlsql_task_id = Column(Integer, ForeignKey("nlsql_task_config.id", ondelete="CASCADE"), nullable=False)
    sql = Column(Text, nullable=False, comment="SQL")
    where_conditions = Column(Text, comment="WHERE条件")
    tables = Column(Text, comment="使用的表")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    nlsql_task = relationship("NlsqlTaskConfig")

    class Config:
        from_attributes = True

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship
from app.core.database import Base


class TableFieldRelation(Base):
    __tablename__ = "table_field_relation"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    nlsql_task_id = Column(Integer, ForeignKey("nlsql_task_config.id", ondelete="CASCADE"), nullable=False)
    source_table_field_prompt_id = Column(Integer, ForeignKey("table_field_prompt.id", ondelete="SET NULL"), nullable=True)
    source_table_level_prompt_id = Column(Integer, ForeignKey("table_level_prompt.id", ondelete="SET NULL"), nullable=True)
    source_table_name = Column(String(255), nullable=True, comment="源表名称")
    source_field_name = Column(String(255), nullable=True, comment="源字段名称")
    target_table_field_prompt_id = Column(Integer, ForeignKey("table_field_prompt.id", ondelete="SET NULL"), nullable=True)
    target_table_level_prompt_id = Column(Integer, ForeignKey("table_level_prompt.id", ondelete="SET NULL"), nullable=True)
    target_table_name = Column(String(255), nullable=True, comment="目标表名称")
    target_field_name = Column(String(255), nullable=True, comment="目标字段名称")
    relation_type = Column(String(100), nullable=False, comment="关联类型")
    relation_description = Column(Text, comment="关联描述")
    confidence = Column(String(16), comment="置信度")
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment="创建时间")

    nlsql_task = relationship("NlsqlTaskConfig")
    source_table_field_prompt = relationship("TableFieldPrompt", foreign_keys=[source_table_field_prompt_id])
    source_table_level_prompt = relationship("TableLevelPrompt", foreign_keys=[source_table_level_prompt_id])
    target_table_field_prompt = relationship("TableFieldPrompt", foreign_keys=[target_table_field_prompt_id])
    target_table_level_prompt = relationship("TableLevelPrompt", foreign_keys=[target_table_level_prompt_id])

    class Config:
        from_attributes = True

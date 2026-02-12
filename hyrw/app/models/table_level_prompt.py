from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, text
from sqlalchemy.orm import relationship
from app.core.database import Base


class TableLevelPrompt(Base):
    __tablename__ = "table_level_prompt"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    task_id = Column(Integer, ForeignKey("nlsql_task_config.id", ondelete="CASCADE"), nullable=False)
    table_metadata_id = Column(Integer, ForeignKey("table_metadata_basic.id", ondelete="CASCADE"), nullable=False)
    table_name = Column(String(255), nullable=False, comment="表名称")
    llm_config_id = Column(Integer, ForeignKey("llm_config.id", ondelete="CASCADE"), nullable=False)

    table_description = Column(Text, comment="表描述")
    query_scenarios = Column(JSON, comment="查询场景列表")
    aggregation_scenarios = Column(JSON, comment="聚合场景列表")
    data_role = Column(JSON, comment="数据角色列表")
    usage_not_scenarios = Column(JSON, comment="不适合场景列表")

    system_config = Column(Text, comment="系统级别描述")
    table_notes = Column(JSON, comment="表注意事项列表")

    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment="创建时间")
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment="更新时间")

    table_metadata = relationship("TableMetadataBasic")
    llm_config = relationship("LlmConfig")

    class Config:
        from_attributes = True

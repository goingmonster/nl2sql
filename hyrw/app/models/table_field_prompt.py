from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, text
from sqlalchemy.orm import relationship
from app.core.database import Base


class TableFieldPrompt(Base):
    __tablename__ = "table_field_prompt"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    nlsql_task_id = Column(Integer, ForeignKey("nlsql_task_config.id", ondelete="CASCADE"), nullable=False)
    table_level_prompt_id = Column(Integer, ForeignKey("table_level_prompt.id", ondelete="CASCADE"), nullable=True)
    field_name = Column(String(255), nullable=False, comment="字段名称")
    business_meaning = Column(Text, comment="业务含义")
    data_format = Column(String(500), comment="数据样式")
    field_description = Column(Text, comment="字段描述")
    query_scenarios = Column(Text, comment="查询场景")
    aggregation_scenarios = Column(Text, comment="聚合场景")
    rules = Column(Text, comment="使用规则")
    database_usage = Column(Text, comment="数据库使用方式")
    field_type = Column(String(100), comment="字段类型")
    null_rate = Column(String(32), comment="空值率")
    unique_count = Column(Integer, comment="唯一值数量")
    sample_values = Column(JSON, comment="样例数据")
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment="创建时间")
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment="更新时间")

    nlsql_task = relationship("NlsqlTaskConfig")
    table_level_prompt = relationship("TableLevelPrompt")

    class Config:
        from_attributes = True

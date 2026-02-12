from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger, JSON, ForeignKey, text
from sqlalchemy.orm import relationship
from app.core.database import Base


class NlsqlTaskConfig(Base):
    __tablename__ = "nlsql_task_config"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    llm_config_id = Column(Integer, ForeignKey("llm_config.id", ondelete="CASCADE"), nullable=False, comment="llm配置外键")
    db_config_id = Column(Integer, ForeignKey("db_config.id", ondelete="CASCADE"), nullable=False, comment="数据库配置外键")
    user_prompt_config_id = Column(Integer, ForeignKey("user_prompt_config.id", ondelete="CASCADE"), nullable=False, comment="提示词生成配置ID")
    select_tables = Column(JSON, comment="选中的表元数据ID列表，格式为数组如[1,2,3]，用于限制NL2SQL查询的表范围")
    description = Column(Text, comment="任务描述")
    status = Column(Integer, default=1, nullable=False, comment="任务状态：1-初始化，2-提取元数据，3-生成表提示词，4-生成字段提示词，5-生成关联关系，6-完成")
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='创建时间')
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='更新时间')

    # 关联关系
    llm_config = relationship("LlmConfig", back_populates="nlsql_tasks")
    db_config = relationship("DbConfig", back_populates="nlsql_tasks")
    user_prompt_config = relationship("UserPromptConfig", back_populates="nlsql_tasks")
    table_metadata_basic = relationship("TableMetadataBasic", back_populates="nlsql_task", cascade="all, delete-orphan")

    # 与其他表的关联（暂时注释，等这些模型创建后再启用）
    # table_level_prompts = relationship("TableLevelPrompt", back_populates="nlsql_task", cascade="all, delete-orphan")
    # table_field_prompts = relationship("TableFieldPrompt", back_populates="nlsql_task", cascade="all, delete-orphan")
    # table_field_relations = relationship("TableFieldRelation", back_populates="nlsql_task", cascade="all, delete-orphan")
    # qa_embeddings = relationship("QaEmbedding", back_populates="nlsql_task", cascade="all, delete-orphan")
    # knowledges = relationship("Knowledge", back_populates="nlsql_task", cascade="all, delete-orphan")
    # conversations = relationship("Conversation", back_populates="nlsql_task", cascade="all, delete-orphan")

    class Config:
        from_attributes = True

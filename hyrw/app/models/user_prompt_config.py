from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserPromptConfig(Base):
    """
    用户提示词配置模型
    """
    __tablename__ = "user_prompt_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    config_name = Column(String(255), nullable=False, comment="配置名称")
    system_config = Column(Text, comment="系统级别的描述")
    table_notes = Column(Text, comment="表级别的描述（JSON列表）")
    field_notes = Column(Text, comment="字段级别的描述（JSON列表）")
    config_type = Column(Integer, comment="配置类型：1-默认，2-自定义，3-系统预制")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 与nlsql_task_config的关联
    nlsql_tasks = relationship("NlsqlTaskConfig", back_populates="user_prompt_config", cascade="all, delete-orphan")
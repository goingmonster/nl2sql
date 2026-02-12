from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class LlmConfig(Base):
    __tablename__ = "llm_config"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    base_url = Column(String(500), nullable=False, comment='URL地址')
    api_key = Column(String(500), nullable=False, comment='API密钥')
    max_tokens = Column(Integer, default=4096, comment='最大token配置')
    temperature = Column(Numeric(3, 2), default=0.7, comment='温度参数')
    description = Column(Text, comment='描述')
    provider = Column(String(100), nullable=False, comment='供应商')
    model_name = Column(String(100), nullable=False, comment='模型名称')
    status = Column(Integer, default=1, comment='状态：1-启用，2-禁用')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')

    # 与nlsql_task_config的关联
    nlsql_tasks = relationship("NlsqlTaskConfig", back_populates="llm_config", cascade="all, delete-orphan")

    
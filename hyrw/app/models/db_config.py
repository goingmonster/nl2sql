from sqlalchemy import Column, Integer, String, DateTime, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class DbConfig(Base):
    __tablename__ = "db_config"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    type = Column(String(50), nullable=False, comment='数据库类型 PG CK MYSQL')
    database_name = Column(String(100), nullable=False, comment='数据库名称')
    schema_name = Column(String(100), default='public', comment='schema名称，默认public postgres 其他的数据库没有')
    ip = Column(String(45), nullable=False, comment='IP地址')
    port = Column(Integer, nullable=False, comment='端口')
    username = Column(String(100), nullable=False, comment='用户名')
    password = Column(String(255), nullable=False, comment='密码')
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='创建时间')
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), comment='更新时间')

    # 与table_metadata的关联
    table_metadata = relationship("TableMetadata", back_populates="db_config", cascade="all, delete-orphan")
    table_metadata_basic = relationship("TableMetadataBasic", back_populates="db_config", cascade="all, delete-orphan")

    # 与nlsql_task_config的关联
    nlsql_tasks = relationship("NlsqlTaskConfig", back_populates="db_config", cascade="all, delete-orphan")

    class Config:
        from_attributes = True
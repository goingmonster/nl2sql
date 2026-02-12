from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TableMetadata(Base):
    __tablename__ = "table_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, comment='主键')
    db_config_id = Column(Integer, ForeignKey('db_config.id', ondelete='CASCADE'), nullable=False, comment='db_config_id外键')
    table_name = Column(String(255), nullable=False, comment='表名称')
    table_description = Column(Text, comment='表描述（人工添加或者自动获取）')
    table_row_count = Column(Integer, comment='表行数')
    table_ddl = Column(Text, comment='创建表语句')
    table_type = Column(String(50), comment='表类型：枚举 事实 日志')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment='更新时间')

    # 与db_config的关联
    db_config = relationship("DbConfig", back_populates="table_metadata")

    class Config:
        from_attributes = True
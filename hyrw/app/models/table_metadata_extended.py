from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TableMetadataBasic(Base):
    """表基础元数据"""
    __tablename__ = "table_metadata_basic"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, comment='主键')
    table_task_id = Column(Integer, ForeignKey('nlsql_task_config.id', ondelete='CASCADE'), nullable=False, comment='NLSQL任务ID')
    db_connection_id = Column(Integer, ForeignKey('db_config.id', ondelete='CASCADE'), nullable=False, comment='数据库连接配置ID')
    schema_name = Column(String(255), nullable=False, comment='模式名')
    table_name = Column(String(255), nullable=False, comment='表名称')
    table_ddl = Column(Text, comment='创建表语句')
    table_row_count = Column(Integer, comment='表行数')
    table_description = Column(Text, comment='表描述')
    table_type = Column(String(50), comment='表类型')
    is_active = Column(Boolean, default=True, comment='是否激活')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment='更新时间')

    # 关联关系
    nlsql_task = relationship("NlsqlTaskConfig", back_populates="table_metadata_basic")
    db_config = relationship("DbConfig", back_populates="table_metadata_basic")
    table_sample_data = relationship("TableSampleData", back_populates="table_metadata", cascade="all, delete-orphan")
    table_field_metadata = relationship("TableFieldMetadata", back_populates="table_metadata", cascade="all, delete-orphan")

    class Config:
        from_attributes = True


class TableSampleData(Base):
    """表样例数据"""
    __tablename__ = "table_sample_data"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, comment='主键')
    table_metadata_id = Column(Integer, ForeignKey('table_metadata_basic.id', ondelete='CASCADE'), nullable=False, comment='表基础元数据ID')
    sample_data = Column(JSON, comment='样例数据JSON')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment='更新时间')

    # 关联关系
    table_metadata = relationship("TableMetadataBasic", back_populates="table_sample_data")

    class Config:
        from_attributes = True


class TableFieldMetadata(Base):
    """表字段元数据"""
    __tablename__ = "table_field_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, comment='主键')
    table_metadata_id = Column(Integer, ForeignKey('table_metadata_basic.id', ondelete='CASCADE'), nullable=False, comment='表基础元数据ID')
    field_name = Column(String(255), nullable=False, comment='字段名')
    field_type = Column(String(255), nullable=False, comment='字段类型')
    null_rate = Column(Float, comment='空值率')
    sample_data = Column(JSON, comment='字段样例数据JSON')
    unique_count = Column(Integer, comment='唯一值数量')
    field_description = Column(Text, comment='字段描述')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment='更新时间')

    # 关联关系
    table_metadata = relationship("TableMetadataBasic", back_populates="table_field_metadata")

    class Config:
        from_attributes = True
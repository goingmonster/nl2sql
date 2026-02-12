from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

# 注意：在 SQLite 中使用 Integer 而不是 BigInteger


class TableMetadataBase(BaseModel):
    db_config_id: int = Field(..., description='数据库配置ID')
    table_name: str = Field(..., min_length=1, max_length=255, description='表名称')
    table_description: Optional[str] = Field(None, description='表描述（人工添加或者自动获取）')
    table_row_count: Optional[int] = Field(None, ge=0, description='表行数')
    table_ddl: Optional[str] = Field(None, description='创建表语句')
    table_type: Optional[str] = Field(None, max_length=50, description='表类型：枚举 事实 日志')


class TableMetadataCreate(TableMetadataBase):
    pass


class TableMetadataUpdate(BaseModel):
    table_name: Optional[str] = Field(None, min_length=1, max_length=255, description='表名称')
    table_description: Optional[str] = Field(None, description='表描述（人工添加或者自动获取）')
    table_row_count: Optional[int] = Field(None, ge=0, description='表行数')
    table_ddl: Optional[str] = Field(None, description='创建表语句')
    table_type: Optional[str] = Field(None, max_length=50, description='表类型：枚举 事实 日志')


class TableMetadata(TableMetadataBase):
    id: int = Field(..., description='主键')
    created_at: datetime = Field(..., description='创建时间')
    updated_at: datetime = Field(..., description='更新时间')

    class Config:
        from_attributes = True


class TableMetadataScanRequest(BaseModel):
    db_config_id: int = Field(..., description='数据库配置ID')


class TableMetadataScanResponse(BaseModel):
    success: bool = Field(..., description='扫描是否成功')
    message: str = Field(..., description='扫描结果消息')


class TableMetadataBatchDelete(BaseModel):
    ids: List[int] = Field(..., min_items=1, description='要删除的ID列表')


class TableMetadataDeleteByConditions(BaseModel):
    db_config_ids: Optional[List[int]] = Field(None, description='数据库配置ID列表')
    table_name: Optional[str] = Field(None, description='表名称（支持精确匹配）')
    table_type: Optional[str] = Field(None, description='表类型')
    min_row_count: Optional[int] = Field(None, ge=0, description='最小行数')
    max_row_count: Optional[int] = Field(None, ge=0, description='最大行数')
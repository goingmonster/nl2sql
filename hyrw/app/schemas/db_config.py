from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class DbConfigBase(BaseModel):
    type: str = Field(..., description="数据库类型 PG CK MYSQL", max_length=50)
    database_name: str = Field(..., description="数据库名称", max_length=100)
    schema_name: Optional[str] = Field(default="public", description="schema名称", max_length=100)
    ip: str = Field(..., description="IP地址", max_length=45)
    port: int = Field(..., description="端口", gt=0, le=65535)
    username: str = Field(..., description="用户名", max_length=100)
    password: str = Field(..., description="密码", max_length=255)


class DbConfigCreate(DbConfigBase):
    pass


class DbConfigUpdate(BaseModel):
    type: Optional[str] = Field(None, description="数据库类型", max_length=50)
    database_name: Optional[str] = Field(None, description="数据库名称", max_length=100)
    schema_name: Optional[str] = Field(None, description="schema名称", max_length=100)
    ip: Optional[str] = Field(None, description="IP地址", max_length=45)
    port: Optional[int] = Field(None, description="端口", gt=0, le=65535)
    username: Optional[str] = Field(None, description="用户名", max_length=100)
    password: Optional[str] = Field(None, description="密码", max_length=255)


class DbConfig(DbConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DbConfigBatchDelete(BaseModel):
    ids: List[int] = Field(..., description="要删除的ID列表")


class PaginatedResponse(BaseModel):
    items: List[DbConfig]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class SearchParams(BaseModel):
    keyword: Optional[str] = Field(None, description="搜索关键词")
    type: Optional[str] = Field(None, description="数据库类型过滤")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class FilterParams(BaseModel):
    type: Optional[str] = Field(None, description="数据库类型")
    database_name: Optional[str] = Field(None, description="数据库名称")
    ip: Optional[str] = Field(None, description="IP地址")
    port: Optional[int] = Field(None, description="端口")
    username: Optional[str] = Field(None, description="用户名")
    schema_name: Optional[str] = Field(None, description="schema名称")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
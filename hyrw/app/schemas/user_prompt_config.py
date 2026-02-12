from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class UserPromptConfigBase(BaseModel):
    """用户提示词配置基础模型"""
    config_name: str = Field(..., description="配置名称", max_length=255)
    system_config: Optional[str] = Field(None, description="系统级别的描述")
    table_notes: Optional[List[str]] = Field(default=[], description="表级别的描述列表")
    field_notes: Optional[List[str]] = Field(default=[], description="字段级别的描述列表")
    config_type: Optional[int] = Field(1, description="配置类型：1-默认，2-自定义，3-系统预制")


class UserPromptConfigCreate(UserPromptConfigBase):
    """创建用户提示词配置"""
    pass


class UserPromptConfigUpdate(BaseModel):
    """更新用户提示词配置"""
    config_name: Optional[str] = Field(None, description="配置名称", max_length=255)
    system_config: Optional[str] = Field(None, description="系统级别的描述")
    table_notes: Optional[List[str]] = Field(None, description="表级别的描述列表")
    field_notes: Optional[List[str]] = Field(None, description="字段级别的描述列表")
    config_type: Optional[int] = Field(None, description="配置类型：1-默认，2-自定义，3-系统预制")


class UserPromptConfigInDB(UserPromptConfigBase):
    """数据库中的用户提示词配置"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SingleConfigResponse(BaseModel):
    """单个用户提示词配置响应"""
    data: UserPromptConfigInDB
    message: str


class ListConfigResponse(BaseModel):
    """用户提示词配置列表响应"""
    data: List[UserPromptConfigInDB]
    total: int
    page: int
    page_size: int
    message: str


class UserPromptConfigBatchDelete(BaseModel):
    """批量删除用户提示词配置"""
    ids: List[int] = Field(..., description="要删除的配置ID列表")
from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class NlsqlTaskConfigBase(BaseModel):
    llm_config_id: int = Field(..., description="LLM配置ID")
    db_config_id: int = Field(..., description="数据库配置ID")
    user_prompt_config_id: int = Field(..., description="用户提示词配置ID")
    select_tables: Optional[List[int]] = Field(None, description="选中的表元数据ID列表")
    description: Optional[str] = Field(None, description="任务描述")
    status: Optional[int] = Field(1, description="任务状态：1-初始化，2-提取元数据，3-生成表提示词，4-生成字段提示词，5-生成关联关系，6-完成")


class NlsqlTaskConfigCreate(NlsqlTaskConfigBase):
    pass


class NlsqlTaskConfigUpdate(BaseModel):
    llm_config_id: Optional[int] = Field(None, description="LLM配置ID")
    db_config_id: Optional[int] = Field(None, description="数据库配置ID")
    user_prompt_config_id: Optional[int] = Field(None, description="用户提示词配置ID")
    select_tables: Optional[List[int]] = Field(None, description="选中的表元数据ID列表")
    description: Optional[str] = Field(None, description="任务描述")
    status: Optional[int] = Field(None, description="任务状态")


class NlsqlTaskConfig(NlsqlTaskConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NlsqlTaskConfigBatchDelete(BaseModel):
    ids: List[int] = Field(..., description="要删除的ID列表")


class NlsqlTaskConfigPaginatedResponse(BaseModel):
    items: List[NlsqlTaskConfig]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class NlsqlTaskConfigSearchParams(BaseModel):
    keyword: Optional[str] = Field(None, description="搜索关键词")
    status: Optional[int] = Field(None, description="任务状态过滤")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class NlsqlTaskConfigFilterParams(BaseModel):
    status: Optional[int] = Field(None, description="任务状态")
    llm_config_id: Optional[int] = Field(None, description="LLM配置ID")
    db_config_id: Optional[int] = Field(None, description="数据库配置ID")
    user_prompt_config_id: Optional[int] = Field(None, description="用户提示词配置ID")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# 带关联信息的响应模型
class NlsqlTaskConfigWithRelations(NlsqlTaskConfig):
    llm_config_name: Optional[str] = Field(None, description="LLM配置名称")
    db_config_name: Optional[str] = Field(None, description="数据库配置名称")
    user_prompt_config_name: Optional[str] = Field(None, description="用户提示词配置名称")


class NlsqlTaskConfigPaginatedWithRelationsResponse(BaseModel):
    items: List[NlsqlTaskConfigWithRelations]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

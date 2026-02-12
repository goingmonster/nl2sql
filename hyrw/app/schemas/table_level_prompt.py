from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TableLevelPromptBase(BaseModel):
    task_id: int = Field(..., description="NLSQL任务ID")
    table_metadata_id: int = Field(..., description="表元数据ID")
    table_name: str = Field(..., description="表名称", max_length=255)
    llm_config_id: int = Field(..., description="LLM配置ID")
    table_description: Optional[str] = Field(None, description="表描述")
    query_scenarios: Optional[List[str]] = Field(default=[], description="查询场景列表")
    aggregation_scenarios: Optional[List[str]] = Field(default=[], description="聚合场景列表")
    data_role: Optional[List[str]] = Field(default=[], description="数据角色列表")
    usage_not_scenarios: Optional[List[str]] = Field(default=[], description="不适合场景列表")
    system_config: Optional[str] = Field(None, description="系统级别描述")
    table_notes: Optional[List[str]] = Field(default=[], description="表注意事项列表")
    is_active: Optional[bool] = Field(True, description="是否激活")


class TableLevelPromptCreate(TableLevelPromptBase):
    pass


class TableLevelPromptUpdate(BaseModel):
    table_description: Optional[str] = Field(None, description="表描述")
    query_scenarios: Optional[List[str]] = Field(None, description="查询场景列表")
    aggregation_scenarios: Optional[List[str]] = Field(None, description="聚合场景列表")
    data_role: Optional[List[str]] = Field(None, description="数据角色列表")
    usage_not_scenarios: Optional[List[str]] = Field(None, description="不适合场景列表")
    system_config: Optional[str] = Field(None, description="系统级别描述")
    table_notes: Optional[List[str]] = Field(None, description="表注意事项列表")
    is_active: Optional[bool] = Field(None, description="是否激活")


class TableLevelPromptInDB(TableLevelPromptBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TableLevelPromptGenerateRequest(BaseModel):
    task_id: int = Field(..., description="NLSQL任务ID")


class TableLevelPromptBatchDelete(BaseModel):
    ids: List[int] = Field(..., description="要删除的提示词ID列表")

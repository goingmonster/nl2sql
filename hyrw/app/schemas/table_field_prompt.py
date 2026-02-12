from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TableFieldPromptBase(BaseModel):
    nlsql_task_id: int = Field(..., description="任务ID")
    table_level_prompt_id: Optional[int] = Field(None, description="表级提示词ID")
    field_name: str = Field(..., description="字段名称")
    business_meaning: Optional[str] = Field(None, description="业务含义")
    data_format: Optional[str] = Field(None, description="数据格式")
    field_description: Optional[str] = Field(None, description="字段描述")
    query_scenarios: Optional[str] = Field(None, description="查询场景(JSON字符串)")
    aggregation_scenarios: Optional[str] = Field(None, description="聚合场景(JSON字符串)")
    rules: Optional[str] = Field(None, description="规则(JSON字符串)")
    database_usage: Optional[str] = Field(None, description="数据库使用方式(JSON字符串)")
    field_type: Optional[str] = Field(None, description="字段类型")
    null_rate: Optional[str] = Field(None, description="空值率")
    unique_count: Optional[int] = Field(None, description="唯一值数量")
    sample_values: Optional[list] = Field(None, description="样例数据")


class TableFieldPromptCreate(TableFieldPromptBase):
    pass


class TableFieldPromptUpdate(BaseModel):
    business_meaning: Optional[str] = None
    data_format: Optional[str] = None
    field_description: Optional[str] = None
    query_scenarios: Optional[str] = None
    aggregation_scenarios: Optional[str] = None
    rules: Optional[str] = None
    database_usage: Optional[str] = None
    field_type: Optional[str] = None
    null_rate: Optional[str] = None
    unique_count: Optional[int] = None
    sample_values: Optional[list] = None


class TableFieldPromptInDB(TableFieldPromptBase):
    id: int
    table_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TableFieldPromptGenerateRequest(BaseModel):
    task_id: int = Field(..., description="任务ID")


class TableFieldPromptBatchDelete(BaseModel):
    ids: List[int] = Field(..., description="要删除的ID列表")

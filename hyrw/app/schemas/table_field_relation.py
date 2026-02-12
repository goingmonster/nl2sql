from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TableFieldRelationBase(BaseModel):
    nlsql_task_id: int = Field(..., description="任务ID")
    source_table_field_prompt_id: Optional[int] = Field(None, description="源字段提示词ID")
    source_table_level_prompt_id: Optional[int] = Field(None, description="源表提示词ID")
    source_table_name: Optional[str] = Field(None, description="源表名")
    source_field_name: Optional[str] = Field(None, description="源字段名")
    target_table_field_prompt_id: Optional[int] = Field(None, description="目标字段提示词ID")
    target_table_level_prompt_id: Optional[int] = Field(None, description="目标表提示词ID")
    target_table_name: Optional[str] = Field(None, description="目标表名")
    target_field_name: Optional[str] = Field(None, description="目标字段名")
    relation_type: str = Field(..., description="关联类型")
    relation_description: Optional[str] = Field(None, description="关联描述")
    confidence: Optional[str] = Field(None, description="置信度")


class TableFieldRelationCreate(TableFieldRelationBase):
    pass


class TableFieldRelationUpdate(BaseModel):
    source_table_name: Optional[str] = None
    source_field_name: Optional[str] = None
    target_table_name: Optional[str] = None
    target_field_name: Optional[str] = None
    relation_type: Optional[str] = None
    relation_description: Optional[str] = None
    confidence: Optional[str] = None
    source_table_field_prompt_id: Optional[int] = None
    source_table_level_prompt_id: Optional[int] = None
    target_table_field_prompt_id: Optional[int] = None
    target_table_level_prompt_id: Optional[int] = None


class TableFieldRelationInDB(TableFieldRelationBase):
    id: int
    source_table_name: Optional[str] = None
    target_table_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TableFieldRelationGenerateRequest(BaseModel):
    task_id: int = Field(..., description="任务ID")


class TableFieldRelationBatchDelete(BaseModel):
    ids: List[int] = Field(..., description="要删除的ID列表")

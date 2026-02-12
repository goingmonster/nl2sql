from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class WhereConditionItem(BaseModel):
    field: str
    operator: str
    value: Any
    description: Optional[str] = None


class QaJsonItem(BaseModel):
    question: str
    sql: str
    where_conditions: Optional[List[WhereConditionItem]] = None
    tables: Optional[List[str]] = None


class QaEmbeddingBase(BaseModel):
    question: str = Field(..., description="问题")
    nlsql_task_id: int = Field(..., description="任务ID")
    sql: str = Field(..., description="SQL")
    where_conditions: Optional[List[WhereConditionItem]] = Field(default=None, description="WHERE条件")
    tables: Optional[List[str]] = Field(default=None, description="使用的表")
    is_enabled: Optional[bool] = Field(default=True, description="是否启用")


class QaEmbeddingCreate(QaEmbeddingBase):
    pass


class QaEmbeddingUpdate(BaseModel):
    question: Optional[str] = None
    sql: Optional[str] = None
    where_conditions: Optional[List[WhereConditionItem]] = None
    tables: Optional[List[str]] = None
    is_enabled: Optional[bool] = None


class QaEmbeddingInDB(QaEmbeddingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QaEmbeddingBatchDelete(BaseModel):
    ids: List[int] = Field(..., description="要删除的ID列表")


class QaEmbeddingImportRequest(BaseModel):
    task_id: int = Field(..., description="任务ID")
    qa_json: List[QaJsonItem] = Field(..., description="问答对JSON列表")


class QaEmbeddingWhereGenerationRequest(BaseModel):
    qa_embedding_ids: List[int] = Field(..., description="qa_embedding ID列表")
    llm_config_id: int = Field(..., description="LLM配置ID")


class QaEmbeddingExportRequest(BaseModel):
    ids: List[int] = Field(..., description="要导出的ID列表")

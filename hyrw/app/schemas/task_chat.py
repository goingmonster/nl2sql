from datetime import datetime
from typing import List, Optional, Any, Dict

from pydantic import BaseModel, Field


class TaskChatAskRequest(BaseModel):
    task_id: int = Field(..., description="任务ID")
    question: str = Field(..., description="用户问题")
    session_id: Optional[int] = Field(None, description="会话ID，不传则创建新会话")
    session_title: Optional[str] = Field(None, description="会话标题")
    description: Optional[str] = Field(None, description="用户描述")
    is_right: Optional[bool] = Field(None, description="是否正确")


class ChatSessionCreateRequest(BaseModel):
    task_id: int = Field(..., description="任务ID")
    session_title: Optional[str] = Field(None, description="会话标题")


class ChatSessionUpdateRequest(BaseModel):
    session_title: Optional[str] = Field(None, description="会话标题")


class ConversationFeedbackUpdateRequest(BaseModel):
    is_right: Optional[bool] = Field(None, description="是否正确")
    description: Optional[str] = Field(None, description="用户描述")
    feedback: Optional[str] = Field(None, description="反馈信息")


class BatchDeleteRequest(BaseModel):
    ids: List[int] = Field(..., description="要批量删除的ID")


class ChatSessionItem(BaseModel):
    id: int
    nlsql_task_id: int
    session_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    conversation_count: int = 0

    class Config:
        from_attributes = True


class ConversationItem(BaseModel):
    id: int
    session_id: int
    question: str
    answer: Optional[str] = None
    description: Optional[str] = None
    nlsql_task_id: int
    is_right: Optional[bool] = None
    sql_generated: Optional[str] = None
    sql_result: Optional[str] = None
    sql_data: Optional[Any] = None
    selected_tables: Optional[Any] = None
    query_context: Optional[Any] = None
    column_patch: Optional[Any] = None
    feedback: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskChatAskResponse(BaseModel):
    session: ChatSessionItem
    conversation: ConversationItem
    select_table_result: Optional[Dict[str, Any]] = None
    query_context: Optional[Any] = None
    column_patch: Optional[Any] = None
    qColumnPatch: Optional[Any] = None
    create_sql_result: Optional[Any] = None

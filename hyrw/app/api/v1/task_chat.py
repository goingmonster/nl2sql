from typing import List, Optional

from fastapi import APIRouter, Query

from app.schemas.common import APIResponse
from app.schemas.pagination import PaginatedResponse
from app.schemas.task_chat import (
    BatchDeleteRequest,
    ChatSessionCreateRequest,
    ChatSessionItem,
    ChatSessionUpdateRequest,
    ConversationFeedbackUpdateRequest,
    ConversationItem,
    TaskChatAskRequest,
    TaskChatAskResponse,
)
from app.services.task_chat import task_chat_service


router = APIRouter()


@router.post("/ask", response_model=APIResponse[TaskChatAskResponse])
def ask_with_task(request: TaskChatAskRequest):
    result = task_chat_service.ask(
        task_id=request.task_id,
        question=request.question,
        session_id=request.session_id,
        session_title=request.session_title,
        description=request.description,
        is_right=request.is_right,
    )
    return {
        "code": 200,
        "message": "问答成功",
        "data": TaskChatAskResponse.model_validate(result),
    }


@router.post("/sessions", response_model=APIResponse[ChatSessionItem])
def create_session(request: ChatSessionCreateRequest):
    item = task_chat_service.create_session(
        task_id=request.task_id,
        session_title=request.session_title,
    )
    return {
        "code": 200,
        "message": "创建成功",
        "data": ChatSessionItem.model_validate(item),
    }


@router.get("/sessions", response_model=PaginatedResponse[List[ChatSessionItem]])
def get_sessions(
    task_id: Optional[int] = Query(None, description="任务ID"),
    keyword: Optional[str] = Query(None, description="会话关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    result = task_chat_service.get_sessions_with_pagination(
        task_id=task_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    items = [ChatSessionItem.model_validate(item) for item in result["items"]]
    return {
        "code": 200,
        "message": "查询成功",
        "data": items,
        "pagination": {
            "page": result["page"],
            "page_size": result["page_size"],
            "total": result["total"],
            "pages": result["pages"],
        },
    }


@router.get("/sessions/{session_id}", response_model=APIResponse[ChatSessionItem])
def get_session(session_id: int):
    item = task_chat_service.get_session(session_id=session_id)
    return {
        "code": 200,
        "message": "查询成功",
        "data": ChatSessionItem.model_validate(item),
    }


@router.put("/sessions/{session_id}", response_model=APIResponse[ChatSessionItem])
def update_session(session_id: int, request: ChatSessionUpdateRequest):
    item = task_chat_service.update_session(
        session_id=session_id,
        session_title=request.session_title,
    )
    return {
        "code": 200,
        "message": "更新成功",
        "data": ChatSessionItem.model_validate(item),
    }


@router.delete("/sessions/{session_id}", response_model=APIResponse[None])
def delete_session(session_id: int):
    task_chat_service.delete_session(session_id=session_id)
    return {
        "code": 200,
        "message": "删除成功",
        "data": None,
    }


@router.post("/sessions/batch-delete", response_model=APIResponse[dict])
def batch_delete_sessions(request: BatchDeleteRequest):
    result = task_chat_service.batch_delete_sessions(ids=request.ids)
    return {
        "code": 200,
        "message": f"成功删除 {result['deleted_count']} 条记录",
        "data": result,
    }


@router.get("/sessions/{session_id}/conversations", response_model=PaginatedResponse[List[ConversationItem]])
def get_session_conversations(
    session_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    result = task_chat_service.get_conversations_with_pagination(
        session_id=session_id,
        page=page,
        page_size=page_size,
    )
    items = [ConversationItem.model_validate(item) for item in result["items"]]
    return {
        "code": 200,
        "message": "查询成功",
        "data": items,
        "pagination": {
            "page": result["page"],
            "page_size": result["page_size"],
            "total": result["total"],
            "pages": result["pages"],
        },
    }


@router.patch("/conversations/{conversation_id}/feedback", response_model=APIResponse[ConversationItem])
def update_conversation_feedback(conversation_id: int, request: ConversationFeedbackUpdateRequest):
    item = task_chat_service.update_conversation_feedback(
        conversation_id=conversation_id,
        is_right=request.is_right,
        description=request.description,
        feedback=request.feedback,
    )
    return {
        "code": 200,
        "message": "更新成功",
        "data": ConversationItem.model_validate(item),
    }

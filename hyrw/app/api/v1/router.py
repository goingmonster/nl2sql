from fastapi import APIRouter

from .db_config import router as db_config_router
from .llm_config import router as llm_config_router
from .table_metadata import router as table_metadata_router
from .user_prompt_config import router as user_prompt_config_router
from .nlsql_task_config import router as nlsql_task_config_router
from .table_level_prompt import router as table_level_prompt_router
from .table_field_prompt import router as table_field_prompt_router
from .table_field_relation import router as table_field_relation_router
from .qa_embedding import router as qa_embedding_router
from .metadata_scan import router as metadata_scan_router
from .task_chat import router as task_chat_router

api_router = APIRouter()

@api_router.get("/")
async def api_root():
    return {"message": "API V1 is running"}

api_router.include_router(db_config_router, prefix="/db-config", tags=["数据库配置"])
api_router.include_router(llm_config_router, prefix="/llm-config", tags=["LLM配置"])
api_router.include_router(table_metadata_router, prefix="/table-metadata", tags=["表元数据"])
api_router.include_router(user_prompt_config_router, prefix="/user-prompt-config", tags=["用户提示词配置"])
api_router.include_router(nlsql_task_config_router, prefix="/nlsql-task-config", tags=["NLSQL任务配置"])
api_router.include_router(table_level_prompt_router, prefix="/table-level-prompt", tags=["表级别提示词"])
api_router.include_router(table_field_prompt_router, prefix="/table-field-prompt", tags=["字段提示词"])
api_router.include_router(table_field_relation_router, prefix="/table-field-relation", tags=["字段关联关系"])
api_router.include_router(qa_embedding_router, prefix="/qa-embedding", tags=["问答对"])
api_router.include_router(metadata_scan_router, prefix="/metadata", tags=["元数据扫描"])
api_router.include_router(task_chat_router, prefix="/task-chat", tags=["任务问答会话"])

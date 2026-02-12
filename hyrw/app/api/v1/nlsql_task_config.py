from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.nlsql_task_config import nlsql_task_config_service
from app.schemas.nlsql_task_config import (
    NlsqlTaskConfig,
    NlsqlTaskConfigCreate,
    NlsqlTaskConfigUpdate,
    NlsqlTaskConfigBatchDelete,
    NlsqlTaskConfigPaginatedResponse,
    NlsqlTaskConfigPaginatedWithRelationsResponse,
    NlsqlTaskConfigSearchParams,
    NlsqlTaskConfigFilterParams
)

router = APIRouter()


@router.get("/", response_model=NlsqlTaskConfigPaginatedWithRelationsResponse)
async def get_nlsql_task_configs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: int = Query(None, description="任务状态过滤"),
    llm_config_id: int = Query(None, description="LLM配置ID过滤"),
    db_config_id: int = Query(None, description="数据库配置ID过滤"),
    user_prompt_config_id: int = Query(None, description="用户提示词配置ID过滤"),
    description: str = Query(None, description="任务描述过滤"),
    db: AsyncSession = Depends(get_db)
) -> Any:
    filters = {}
    if status is not None:
        filters["status"] = status
    if llm_config_id is not None:
        filters["llm_config_id"] = llm_config_id
    if db_config_id is not None:
        filters["db_config_id"] = db_config_id
    if user_prompt_config_id is not None:
        filters["user_prompt_config_id"] = user_prompt_config_id
    if description:
        filters["description"] = description

    result = await nlsql_task_config_service.get_all_with_pagination_and_relations(
        db=db,
        page=page,
        page_size=page_size,
        filters=filters
    )
    return result


@router.get("/search", response_model=NlsqlTaskConfigPaginatedResponse)
async def search_nlsql_task_configs(
    keyword: str = Query(None, description="搜索关键词"),
    status: int = Query(None, description="任务状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
) -> Any:
    result = await nlsql_task_config_service.search(
        db=db,
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size
    )
    return result


@router.post("/", response_model=NlsqlTaskConfig)
async def create_nlsql_task_config(
    config_in: NlsqlTaskConfigCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    config = await nlsql_task_config_service.create(db=db, obj_in=config_in.dict())
    return config


@router.delete("/batch", response_model=Dict[str, Any])
async def batch_delete_nlsql_task_configs(
    batch_delete: NlsqlTaskConfigBatchDelete,
    db: AsyncSession = Depends(get_db)
) -> Any:
    if not batch_delete.ids:
        raise HTTPException(status_code=400, detail="请提供要删除的ID列表")

    deleted_count = await nlsql_task_config_service.delete_multiple(
        db=db,
        ids=batch_delete.ids
    )

    return {
        "message": f"成功删除 {deleted_count} 条记录",
        "deleted_count": deleted_count,
        "requested_ids": batch_delete.ids
    }


@router.get("/{id}", response_model=NlsqlTaskConfig)
async def get_nlsql_task_config(
    id: int,
    db: AsyncSession = Depends(get_db)
) -> Any:
    config = await nlsql_task_config_service.get_by_id(db, id=id)
    if not config:
        raise HTTPException(status_code=404, detail="任务配置不存在")
    return config


@router.put("/{id}", response_model=NlsqlTaskConfig)
async def update_nlsql_task_config(
    id: int,
    config_in: NlsqlTaskConfigUpdate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    updated_config = await nlsql_task_config_service.update(
        db=db,
        id=id,
        obj_in=config_in.dict(exclude_unset=True)
    )
    return updated_config


@router.delete("/{id}", response_model=NlsqlTaskConfig)
async def delete_nlsql_task_config(
    id: int,
    db: AsyncSession = Depends(get_db)
) -> Any:
    deleted_config = await nlsql_task_config_service.delete(db=db, id=id)
    return deleted_config
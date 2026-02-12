from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.db_config import db_config_service
from app.schemas.db_config import (
    DbConfig,
    DbConfigCreate,
    DbConfigUpdate,
    DbConfigBatchDelete,
    PaginatedResponse,
    SearchParams,
    FilterParams
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def get_db_configs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    type: str = Query(None, description="数据库类型过滤"),
    database_name: str = Query(None, description="数据库名称过滤"),
    ip: str = Query(None, description="IP地址过滤"),
    port: int = Query(None, description="端口过滤"),
    username: str = Query(None, description="用户名过滤"),
    schema_name: str = Query(None, description="schema名称过滤"),
    db: AsyncSession = Depends(get_db)
) -> Any:
    filters = {}
    if type:
        filters["type"] = type
    if database_name:
        filters["database_name"] = database_name
    if ip:
        filters["ip"] = ip
    if port is not None:
        filters["port"] = port
    if username:
        filters["username"] = username
    if schema_name:
        filters["schema_name"] = schema_name

    result = await db_config_service.get_all_with_pagination(
        db=db,
        page=page,
        page_size=page_size,
        filters=filters
    )
    return result


@router.get("/search", response_model=PaginatedResponse)
async def search_db_configs(
    keyword: str = Query(None, description="搜索关键词"),
    type_filter: str = Query(None, alias="type", description="数据库类型过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
) -> Any:
    result = await db_config_service.search(
        db=db,
        keyword=keyword,
        type_filter=type_filter,
        page=page,
        page_size=page_size
    )
    return result


@router.post("/", response_model=DbConfig)
async def create_db_config(
    config_in: DbConfigCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    try:
        config = await db_config_service.create(db=db, obj_in=config_in.dict())
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/batch", response_model=Dict[str, Any])
async def batch_delete_db_configs(
    batch_delete: DbConfigBatchDelete,
    db: AsyncSession = Depends(get_db)
) -> Any:
    if not batch_delete.ids:
        raise HTTPException(status_code=400, detail="请提供要删除的ID列表")

    deleted_count = await db_config_service.delete_multiple(
        db=db,
        ids=batch_delete.ids
    )

    return {
        "message": f"成功删除 {deleted_count} 条记录",
        "deleted_count": deleted_count,
        "requested_ids": batch_delete.ids
    }


@router.get("/{id}", response_model=DbConfig)
async def get_db_config(
    id: int,
    db: AsyncSession = Depends(get_db)
) -> Any:
    config = await db_config_service.get_by_id(db, id=id)
    if not config:
        raise HTTPException(status_code=404, detail="数据库配置不存在")
    return config


@router.put("/{id}", response_model=DbConfig)
async def update_db_config(
    id: int,
    config_in: DbConfigUpdate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    config = await db_config_service.get_by_id(db, id=id)
    if not config:
        raise HTTPException(status_code=404, detail="数据库配置不存在")

    try:
        updated_config = await db_config_service.update(
            db=db,
            id=id,
            obj_in=config_in.dict(exclude_unset=True)
        )
        return updated_config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", response_model=DbConfig)
async def delete_db_config(
    id: int,
    db: AsyncSession = Depends(get_db)
) -> Any:
    config = await db_config_service.get_by_id(db, id=id)
    if not config:
        raise HTTPException(status_code=404, detail="数据库配置不存在")

    deleted_config = await db_config_service.delete(db=db, id=id)
    return deleted_config
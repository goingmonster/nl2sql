from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.user_prompt_config import user_prompt_config_service
from app.schemas.user_prompt_config import (
    UserPromptConfigCreate,
    UserPromptConfigUpdate,
    SingleConfigResponse,
    ListConfigResponse,
    UserPromptConfigBatchDelete
)

router = APIRouter()


@router.post("/", response_model=SingleConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_user_prompt_config(
    *,
    db: AsyncSession = Depends(get_db),
    config_in: UserPromptConfigCreate
):
    """
    创建用户提示词配置
    """
    config = await user_prompt_config_service.create(db, obj_in=config_in)
    return SingleConfigResponse(data=config, message="创建成功")


@router.get("/{id}", response_model=SingleConfigResponse)
async def get_user_prompt_config(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取单个用户提示词配置
    """
    config = await user_prompt_config_service.get_by_id(db, id=id)
    return SingleConfigResponse(data=config, message="获取成功")


@router.get("/", response_model=ListConfigResponse)
async def get_user_prompt_configs(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    config_name: Optional[str] = Query(None, description="配置名称（支持模糊查询）"),
    config_type: Optional[int] = Query(None, description="配置类型：1-默认，2-自定义，3-系统预制")
):
    """
    获取用户提示词配置列表（支持分页和过滤）
    """
    configs, total = await user_prompt_config_service.get_multi(
        db,
        skip=skip,
        limit=limit,
        config_name=config_name,
        config_type=config_type
    )

    return ListConfigResponse(
        data=configs,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        message="获取成功"
    )


@router.put("/{id}", response_model=SingleConfigResponse)
async def update_user_prompt_config(
    id: int,
    *,
    db: AsyncSession = Depends(get_db),
    config_in: UserPromptConfigUpdate
):
    """
    更新用户提示词配置
    """
    config = await user_prompt_config_service.update(db, id=id, obj_in=config_in)
    return SingleConfigResponse(data=config, message="更新成功")


@router.delete("/{id}", response_model=SingleConfigResponse)
async def delete_user_prompt_config(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除单个用户提示词配置
    """
    config = await user_prompt_config_service.delete(db, id=id)
    return SingleConfigResponse(data=config, message="删除成功")


@router.post("/batch-delete")
async def batch_delete_user_prompt_configs(
    *,
    db: AsyncSession = Depends(get_db),
    delete_request: UserPromptConfigBatchDelete
):
    """
    批量删除用户提示词配置
    """
    configs = await user_prompt_config_service.delete_batch(db, ids=delete_request.ids)
    return {
        "message": f"成功删除 {len(configs)} 个配置",
        "deleted_count": len(configs),
        "deleted_ids": [config.id for config in configs]
    }


@router.get("/name/{config_name}", response_model=SingleConfigResponse)
async def get_user_prompt_config_by_name(
    config_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    根据配置名称获取用户提示词配置
    """
    config = await user_prompt_config_service.get_by_name(db, config_name=config_name)
    return SingleConfigResponse(data=config, message="获取成功")


@router.get("/type/{config_type}", response_model=ListConfigResponse)
async def get_user_prompt_configs_by_type(
    config_type: int,
    db: AsyncSession = Depends(get_db)
):
    """
    根据配置类型获取用户提示词配置
    """
    configs = await user_prompt_config_service.get_by_type(db, config_type=config_type)

    return ListConfigResponse(
        data=configs,
        total=len(configs),
        page=1,
        page_size=len(configs),
        message="获取成功"
    )
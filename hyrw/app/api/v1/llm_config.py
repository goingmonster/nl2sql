from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.llm_config import (
    LlmConfigCreate,
    LlmConfigUpdate,
    LlmConfigResponse,
    LlmConfigQuery
)
from app.schemas.common import APIResponse
from app.schemas.pagination import PaginatedResponse
from app.services.llm_config import llm_config_service

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[List[LlmConfigResponse]])
async def get_llm_configs(
    provider: Optional[str] = Query(None, description="供应商"),
    status: Optional[int] = Query(None, ge=1, le=2, description="状态：1-启用，2-禁用"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取LLM配置列表（支持分页和筛选）
    """
    result = await llm_config_service.get_multi_with_pagination(
        db,
        provider=provider,
        status=status,
        page=page,
        page_size=page_size
    )

    # 转换为响应模型
    items = [
        LlmConfigResponse.model_validate(item)
        for item in result['items']
    ]

    return {
        'code': 200,
        'message': '查询成功',
        'data': items,
        'pagination': {
            'page': result['page'],
            'page_size': result['page_size'],
            'total': result['total'],
            'pages': result['pages']
        }
    }


@router.get("/{id}", response_model=APIResponse[LlmConfigResponse])
async def get_llm_config(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取单个LLM配置
    """
    obj = await llm_config_service.get(db, id=id)
    return {
        'code': 200,
        'message': '查询成功',
        'data': LlmConfigResponse.model_validate(obj)
    }


@router.post("/", response_model=APIResponse[LlmConfigResponse])
async def create_llm_config(
    obj_in: LlmConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新的LLM配置
    """
    obj = await llm_config_service.create(db, obj_in=obj_in)
    return {
        'code': 200,
        'message': '创建成功',
        'data': LlmConfigResponse.model_validate(obj)
    }


@router.put("/{id}", response_model=APIResponse[LlmConfigResponse])
async def update_llm_config(
    id: int,
    obj_in: LlmConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    更新LLM配置
    """
    obj = await llm_config_service.update(db, id=id, obj_in=obj_in)
    return {
        'code': 200,
        'message': '更新成功',
        'data': LlmConfigResponse.model_validate(obj)
    }


@router.delete("/{id}", response_model=APIResponse[None])
async def delete_llm_config(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除单个LLM配置
    """
    await llm_config_service.delete(db, id=id)
    return {
        'code': 200,
        'message': '删除成功',
        'data': None
    }


@router.delete("/batch/bulk")
async def batch_delete_llm_configs(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    批量删除LLM配置
    """
    # 从查询参数中获取ids数组，支持ids[]=4&ids[]=5&ids[]=6格式
    ids_param = request.query_params.getlist("ids")
    if not ids_param:
        raise HTTPException(status_code=400, detail="请提供要删除的ID列表")

    try:
        # 转换为整数列表
        ids = [int(id_str) for id_str in ids_param]
    except ValueError:
        raise HTTPException(status_code=400, detail="ID列表格式错误")

    result = await llm_config_service.delete_multi(db, ids=ids)
    return {
        'code': 200,
        'message': f"成功删除 {result['deleted_count']} 条配置",
        'data': result
    }


@router.get("/provider/{provider}", response_model=APIResponse[List[LlmConfigResponse]])
async def get_llm_configs_by_provider(
    provider: str,
    db: AsyncSession = Depends(get_db)
):
    """
    根据供应商获取LLM配置列表
    """
    objs = await llm_config_service.get_by_provider(db, provider=provider)
    return {
        'code': 200,
        'message': '查询成功',
        'data': [LlmConfigResponse.model_validate(obj) for obj in objs]
    }


@router.post("/{id}/enable", response_model=APIResponse[LlmConfigResponse])
async def enable_llm_config(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    启用LLM配置
    """
    obj = await llm_config_service.enable(db, id=id)
    return {
        'code': 200,
        'message': '启用成功',
        'data': LlmConfigResponse.model_validate(obj)
    }


@router.post("/{id}/disable", response_model=APIResponse[LlmConfigResponse])
async def disable_llm_config(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    禁用LLM配置
    """
    obj = await llm_config_service.disable(db, id=id)
    return {
        'code': 200,
        'message': '禁用成功',
        'data': LlmConfigResponse.model_validate(obj)
    }
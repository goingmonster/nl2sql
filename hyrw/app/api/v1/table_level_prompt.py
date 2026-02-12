from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.table_level_prompt import (
    TableLevelPromptCreate,
    TableLevelPromptUpdate,
    TableLevelPromptInDB,
    TableLevelPromptGenerateRequest,
    TableLevelPromptBatchDelete
)
from app.schemas.common import APIResponse
from app.schemas.pagination import PaginatedResponse
from app.services.table_level_prompt import table_level_prompt_service

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[List[TableLevelPromptInDB]])
async def get_table_level_prompts(
    table_name: Optional[str] = Query(None, description="表名过滤"),
    task_id: Optional[int] = Query(None, description="任务ID过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    result = await table_level_prompt_service.get_multi_with_pagination(
        db,
        page=page,
        page_size=page_size,
        table_name=table_name,
        task_id=task_id
    )

    items = [TableLevelPromptInDB.model_validate(item) for item in result["items"]]

    return {
        "code": 200,
        "message": "查询成功",
        "data": items,
        "pagination": {
            "page": result["page"],
            "page_size": result["page_size"],
            "total": result["total"],
            "pages": result["pages"]
        }
    }


@router.get("/{id}", response_model=APIResponse[TableLevelPromptInDB])
async def get_table_level_prompt(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    obj = await table_level_prompt_service.get(db, id=id)
    return {
        "code": 200,
        "message": "查询成功",
        "data": TableLevelPromptInDB.model_validate(obj)
    }


@router.post("/", response_model=APIResponse[TableLevelPromptInDB])
async def create_table_level_prompt(
    obj_in: TableLevelPromptCreate,
    db: AsyncSession = Depends(get_db)
):
    obj = await table_level_prompt_service.create(db, obj_in=obj_in.model_dump())
    return {
        "code": 200,
        "message": "创建成功",
        "data": TableLevelPromptInDB.model_validate(obj)
    }


@router.put("/{id}", response_model=APIResponse[TableLevelPromptInDB])
async def update_table_level_prompt(
    id: int,
    obj_in: TableLevelPromptUpdate,
    db: AsyncSession = Depends(get_db)
):
    obj = await table_level_prompt_service.update(db, id=id, obj_in=obj_in.model_dump(exclude_unset=True))
    return {
        "code": 200,
        "message": "更新成功",
        "data": TableLevelPromptInDB.model_validate(obj)
    }


@router.delete("/{id}", response_model=APIResponse[None])
async def delete_table_level_prompt(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    await table_level_prompt_service.delete(db, id=id)
    return {
        "code": 200,
        "message": "删除成功",
        "data": None
    }


@router.post("/batch-delete", response_model=APIResponse[dict])
async def batch_delete_table_level_prompts(
    delete_request: TableLevelPromptBatchDelete,
    db: AsyncSession = Depends(get_db)
):
    result = await table_level_prompt_service.delete_multi(db, ids=delete_request.ids)
    return {
        "code": 200,
        "message": f"成功删除 {result['deleted_count']} 条记录",
        "data": result
    }


@router.post("/generate", response_model=APIResponse[dict])
async def generate_table_level_prompts(
    request: TableLevelPromptGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await table_level_prompt_service.generate_by_task_id(db, task_id=request.task_id)
    return {
        "code": 200,
        "message": "生成成功",
        "data": result
    }

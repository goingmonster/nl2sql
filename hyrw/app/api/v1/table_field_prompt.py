from typing import List, Optional
from fastapi import APIRouter, Query

from app.schemas.table_field_prompt import (
    TableFieldPromptCreate,
    TableFieldPromptUpdate,
    TableFieldPromptInDB,
    TableFieldPromptGenerateRequest,
    TableFieldPromptBatchDelete
)
from app.schemas.common import APIResponse
from app.schemas.pagination import PaginatedResponse
from app.services.table_field_prompt import table_field_prompt_service


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[List[TableFieldPromptInDB]])
def get_table_field_prompts(
    task_id: Optional[int] = Query(None, description="任务ID过滤"),
    table_name: Optional[str] = Query(None, description="表名过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    result = table_field_prompt_service.get_multi_with_pagination(
        page=page,
        page_size=page_size,
        task_id=task_id,
        table_name=table_name
    )
    items = [TableFieldPromptInDB.model_validate(item) for item in result["items"]]
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


@router.get("/{id}", response_model=APIResponse[TableFieldPromptInDB])
def get_table_field_prompt(id: int):
    obj = table_field_prompt_service.get(id=id)
    return {
        "code": 200,
        "message": "查询成功",
        "data": TableFieldPromptInDB.model_validate(obj)
    }


@router.post("/", response_model=APIResponse[TableFieldPromptInDB])
def create_table_field_prompt(obj_in: TableFieldPromptCreate):
    obj = table_field_prompt_service.create(obj_in.model_dump())
    return {
        "code": 200,
        "message": "创建成功",
        "data": TableFieldPromptInDB.model_validate(obj)
    }


@router.put("/{id}", response_model=APIResponse[TableFieldPromptInDB])
def update_table_field_prompt(id: int, obj_in: TableFieldPromptUpdate):
    obj = table_field_prompt_service.update(id=id, obj_in=obj_in.model_dump(exclude_unset=True))
    return {
        "code": 200,
        "message": "更新成功",
        "data": TableFieldPromptInDB.model_validate(obj)
    }


@router.delete("/{id}", response_model=APIResponse[None])
def delete_table_field_prompt(id: int):
    table_field_prompt_service.delete(id=id)
    return {
        "code": 200,
        "message": "删除成功",
        "data": None
    }


@router.post("/batch-delete", response_model=APIResponse[dict])
def batch_delete_table_field_prompts(delete_request: TableFieldPromptBatchDelete):
    result = table_field_prompt_service.delete_multi(ids=delete_request.ids)
    return {
        "code": 200,
        "message": f"成功删除 {result['deleted_count']} 条记录",
        "data": result
    }


@router.post("/generate", response_model=APIResponse[dict])
def generate_table_field_prompts(request: TableFieldPromptGenerateRequest):
    result = table_field_prompt_service.generate_by_task_id(task_id=request.task_id)
    return {
        "code": 200,
        "message": "生成成功",
        "data": result
    }

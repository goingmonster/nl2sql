from typing import List, Optional
from fastapi import APIRouter, Query

from app.schemas.common import APIResponse
from app.schemas.pagination import PaginatedResponse
from app.schemas.qa_embedding import (
    QaEmbeddingCreate,
    QaEmbeddingUpdate,
    QaEmbeddingInDB,
    QaEmbeddingBatchDelete,
    QaEmbeddingImportRequest,
    QaEmbeddingWhereGenerationRequest,
    QaEmbeddingExportRequest,
    QaJsonItem,
)
from app.services.qa_embedding import qa_embedding_service


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[List[QaEmbeddingInDB]])
def get_qa_embeddings(
    task_id: Optional[int] = Query(None, description="任务ID过滤"),
    question: Optional[str] = Query(None, description="问题关键词"),
    is_enabled: Optional[bool] = Query(None, description="是否启用"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    result = qa_embedding_service.get_multi_with_pagination(
        page=page,
        page_size=page_size,
        task_id=task_id,
        question=question,
        is_enabled=is_enabled,
    )
    items = [QaEmbeddingInDB.model_validate(item) for item in result["items"]]
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


@router.get("/{id}", response_model=APIResponse[QaEmbeddingInDB])
def get_qa_embedding(id: int):
    obj = qa_embedding_service.get(id=id)
    return {"code": 200, "message": "查询成功", "data": QaEmbeddingInDB.model_validate(obj)}


@router.post("/", response_model=APIResponse[QaEmbeddingInDB])
def create_qa_embedding(obj_in: QaEmbeddingCreate):
    obj = qa_embedding_service.create(obj_in.model_dump())
    return {"code": 200, "message": "创建成功", "data": QaEmbeddingInDB.model_validate(obj)}


@router.put("/{id}", response_model=APIResponse[QaEmbeddingInDB])
def update_qa_embedding(id: int, obj_in: QaEmbeddingUpdate):
    obj = qa_embedding_service.update(id=id, obj_in=obj_in.model_dump(exclude_unset=True))
    return {"code": 200, "message": "更新成功", "data": QaEmbeddingInDB.model_validate(obj)}


@router.delete("/{id}", response_model=APIResponse[None])
def delete_qa_embedding(id: int):
    qa_embedding_service.delete(id=id)
    return {"code": 200, "message": "删除成功", "data": None}


@router.post("/batch-delete", response_model=APIResponse[dict])
def batch_delete_qa_embedding(request: QaEmbeddingBatchDelete):
    result = qa_embedding_service.delete_multi(ids=request.ids)
    return {"code": 200, "message": f"成功删除 {result['deleted_count']} 条记录", "data": result}


@router.post("/import", response_model=APIResponse[dict])
def import_qa_embedding(request: QaEmbeddingImportRequest):
    result = qa_embedding_service.import_qa_pairs(task_id=request.task_id, qa_json=[item.model_dump() for item in request.qa_json])
    return {"code": 200, "message": "导入成功", "data": result}


@router.post("/generate-where-conditions", response_model=APIResponse[dict])
def generate_where_conditions(request: QaEmbeddingWhereGenerationRequest):
    result = qa_embedding_service.generate_where_conditions(
        qa_embedding_ids=request.qa_embedding_ids,
        llm_config_id=request.llm_config_id,
    )
    return {"code": 200, "message": "生成完成", "data": result}


@router.post("/export", response_model=APIResponse[List[QaJsonItem]])
def export_qa_embeddings(request: QaEmbeddingExportRequest):
    result = qa_embedding_service.export_qa_pairs(ids=request.ids)
    return {"code": 200, "message": f"导出成功，共 {len(result)} 条记录", "data": result}

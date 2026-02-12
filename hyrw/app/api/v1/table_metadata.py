from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.table_metadata import (
    TableMetadata,
    TableMetadataScanRequest,
    TableMetadataScanResponse,
    TableMetadataBatchDelete,
    TableMetadataDeleteByConditions
)
from app.services.table_metadata_service import table_metadata_service
from app.crud import table_metadata, db_config

router = APIRouter()


@router.post("/scan", response_model=TableMetadataScanResponse)
async def scan_tables(
    request: TableMetadataScanRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    扫描数据库表元数据
    - **db_config_id**: 数据库配置ID
    """
    result = await table_metadata_service.scan_tables(db, request.db_config_id)
    return result


@router.get("/")
async def get_table_metadata_list(
    db_config_id: Optional[int] = None,
    table_name: Optional[str] = None,
    table_type: Optional[str] = None,
    min_row_count: Optional[int] = None,
    max_row_count: Optional[int] = None,
    order_by: Optional[str] = "created_at",
    order_direction: Optional[str] = "desc",
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    获取表元数据列表（带高级查询功能）
    - **db_config_id**: 数据库配置ID（可选）
    - **table_name**: 表名称（支持模糊搜索）
    - **table_type**: 表类型（可选：TABLE/VIEW/LOG/FACT等）
    - **min_row_count**: 最小行数（可选）
    - **max_row_count**: 最大行数（可选）
    - **order_by**: 排序字段（可选，默认created_at）
    - **order_direction**: 排序方向（asc/desc，默认desc）
    - **skip**: 跳过记录数（分页）
    - **limit**: 限制记录数（分页）
    """
    # 验证db_config_id是否存在
    if db_config_id is not None:
        db_config_obj = await db_config.crud_db_config.get(db, db_config_id)
        if not db_config_obj:
            raise HTTPException(status_code=404, detail=f"数据库配置不存在，ID: {db_config_id}")

    # 获取数据
    items = await table_metadata.crud_table_metadata.get_multi_with_filters(
        db,
        db_config_ids=[db_config_id] if db_config_id is not None else None,
        table_name=table_name,
        table_type=table_type,
        min_row_count=min_row_count,
        max_row_count=max_row_count,
        order_by=order_by,
        order_direction=order_direction,
        skip=skip,
        limit=limit
    )

    # 获取总数
    total = await table_metadata.crud_table_metadata.get_count_with_filters(
        db,
        db_config_ids=[db_config_id] if db_config_id is not None else None,
        table_name=table_name,
        table_type=table_type,
        min_row_count=min_row_count,
        max_row_count=max_row_count
    )

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }




@router.delete("/by-conditions")
async def delete_table_metadata_by_conditions(
    request: TableMetadataDeleteByConditions,
    db: AsyncSession = Depends(get_db)
):
    """
    根据条件批量删除表元数据
    - **db_config_ids**: 数据库配置ID列表（可选）
    - **table_name**: 表名称（精确匹配，可选）
    - **table_type**: 表类型（可选）
    - **min_row_count**: 最小行数（可选）
    - **max_row_count**: 最大行数（可选）
    """
    # 构建删除条件
    conditions = {}
    if request.db_config_ids:
        conditions["db_config_id"] = request.db_config_ids
    if request.table_name:
        conditions["table_name"] = request.table_name
    if request.table_type:
        conditions["table_type"] = request.table_type

    # 处理行数范围条件
    if request.min_row_count is not None:
        conditions["table_row_count_gte"] = request.min_row_count
    if request.max_row_count is not None:
        conditions["table_row_count_lte"] = request.max_row_count

    # 如果只有行数条件，需要特殊处理
    if not conditions and (request.min_row_count is not None or request.max_row_count is not None):
        # 先查询所有记录，然后根据行数范围删除
        deleted_items = await table_metadata.crud_table_metadata.get_multi_with_filters(
            db,
            min_row_count=request.min_row_count,
            max_row_count=request.max_row_count,
            skip=0,
            limit=10000  # 假设一个较大的限制
        )
        if deleted_items:
            ids_to_delete = [item.id for item in deleted_items]
            await table_metadata.crud_table_metadata.delete_multiple(db, ids_to_delete)
            return {
                "message": f"成功删除 {len(deleted_items)} 条记录",
                "deleted_items": deleted_items
            }
        else:
            raise HTTPException(status_code=404, detail="没有找到符合条件的记录")
    else:
        # 使用条件删除
        result = []
        if conditions:
            result = await table_metadata.crud_table_metadata.delete_by_conditions(db, conditions)

        if not result and request.min_row_count is None and request.max_row_count is None:
            raise HTTPException(status_code=404, detail="没有找到符合条件的记录")

        return {
            "message": f"成功删除 {len(result)} 条记录",
            "deleted_items": result
        }


@router.get("/{table_id}", response_model=TableMetadata)
async def get_table_metadata(
    table_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取单个表元数据
    - **table_id**: 表元数据ID
    """
    table = await table_metadata.crud_table_metadata.get(db, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="表元数据不存在")
    return table


@router.delete("/batch")
async def delete_table_metadata_batch(
    request: TableMetadataBatchDelete,
    db: AsyncSession = Depends(get_db)
):
    """
    批量删除表元数据（级联删除样例数据和字段元数据）
    - **ids**: 要删除的 ID 列表
    """
    if not request.ids:
        raise HTTPException(status_code=400, detail="ID列表不能为空")

    deleted_items = await table_metadata.crud_table_metadata.delete_multiple(db, request.ids)
    if not deleted_items:
        raise HTTPException(status_code=404, detail="没有找到要删除的记录")
    return {
        "message": f"成功删除 {len(deleted_items)} 条记录（含级联删除的样例数据和字段元数据）",
        "deleted_items": deleted_items
    }


@router.delete("/{table_id}")
async def delete_table_metadata(
    table_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除表元数据（级联删除样例数据和字段元数据）
    - **table_id**: 表元数据ID
    """
    table = await table_metadata.crud_table_metadata.delete(db, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="表元数据不存在")
    return {"message": "删除成功"}
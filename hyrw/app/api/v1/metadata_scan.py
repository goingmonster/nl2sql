from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.services.metadata_service import MetadataService
from app.schemas.common import APIResponse


class UpdateDescriptionRequest(BaseModel):
    description: str


router = APIRouter()


@router.post("/scan/{task_id}", response_model=APIResponse[Dict[str, Any]])
async def scan_metadata(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    通过 task_id 扫描并提取元数据
    """
    try:
        # 使用同步版本的服务
        result = MetadataService.scan_metadata_by_task_id(task_id)

        return APIResponse(
            code=200,
            message=f"成功扫描任务 {task_id} 的元数据，共扫描 {result['total_tables']} 个表",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"扫描元数据失败: {str(e)}")


@router.get("/task/{task_id}", response_model=APIResponse[Dict[str, Any]])
async def get_metadata_by_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    通过 task_id 获取已扫描的元数据
    """
    try:
        # 使用同步版本的服务
        result = MetadataService.get_metadata_by_task_id(task_id)

        return APIResponse(
            code=200,
            message="成功获取元数据",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取元数据失败: {str(e)}")


@router.get("/table/{table_metadata_id}", response_model=APIResponse[Dict[str, Any]])
async def get_table_metadata_detail(
    table_metadata_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取单个表的详细元数据
    """
    try:
        # 使用同步版本的服务
        result = MetadataService.get_table_metadata_detail(table_metadata_id)

        if not result:
            raise HTTPException(status_code=404, detail=f"表元数据不存在: {table_metadata_id}")

        return APIResponse(
            code=200,
            message="成功获取表详细元数据",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表详细元数据失败: {str(e)}")


@router.put("/table/{table_metadata_id}/description", response_model=APIResponse[Dict[str, str]])
async def update_table_description(
    table_metadata_id: int,
    request: UpdateDescriptionRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    更新表描述
    """
    try:
        # 使用同步版本的服务
        MetadataService.update_table_description(table_metadata_id, request.description)

        return APIResponse(
            code=200,
            message="成功更新表描述",
            data={"status": "success"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新表描述失败: {str(e)}")


@router.put("/field/{field_metadata_id}/description", response_model=APIResponse[Dict[str, str]])
async def update_field_description(
    field_metadata_id: int,
    request: UpdateDescriptionRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    更新字段描述
    """
    try:
        # 使用同步版本的服务
        MetadataService.update_field_description(field_metadata_id, request.description)

        return APIResponse(
            code=200,
            message="成功更新字段描述",
            data={"status": "success"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新字段描述失败: {str(e)}")


@router.delete("/table/batch", response_model=APIResponse[Dict[str, Any]])
async def batch_delete_table_metadata(
    table_ids: List[int] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    批量删除表元数据（级联删除样例数据和字段元数据）
    """
    try:
        deleted_count = 0
        errors = []

        for table_id in table_ids:
            try:
                success = MetadataService.delete_table_metadata(table_id)
                if success:
                    deleted_count += 1
                else:
                    errors.append(f"表ID {table_id} 不存在")
            except Exception as e:
                errors.append(f"删除表ID {table_id} 失败: {str(e)}")

        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="没有找到要删除的表元数据")

        return APIResponse(
            code=200,
            message=f"成功删除 {deleted_count} 条表元数据（含级联删除的样例数据和字段元数据）",
            data={
                "deleted_count": deleted_count,
                "total_requested": len(table_ids),
                "errors": errors
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除表元数据失败: {str(e)}")
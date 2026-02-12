from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.crud.nlsql_task_config import crud_nlsql_task_config
from app.crud.llm_config import crud_llm_config
from app.crud.db_config import crud_db_config
from app.crud.user_prompt_config import crud_user_prompt_config
from app.models.nlsql_task_config import NlsqlTaskConfig
from app.models.llm_config import LlmConfig
from app.models.db_config import DbConfig
from app.models.user_prompt_config import UserPromptConfig
from app.schemas.nlsql_task_config import (
    NlsqlTaskConfigWithRelations,
    NlsqlTaskConfigPaginatedResponse,
    NlsqlTaskConfigPaginatedWithRelationsResponse
)
from app.schemas.pagination import PaginatedResponse
import math


class NlsqlTaskConfigService:
    async def get_by_id(self, db: AsyncSession, id: int) -> Optional[NlsqlTaskConfig]:
        return await crud_nlsql_task_config.get(db, id=id)

    async def get_all_with_pagination(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> NlsqlTaskConfigPaginatedResponse:
        skip = (page - 1) * page_size
        total = await crud_nlsql_task_config.get_count(db, filters=filters)
        items = await crud_nlsql_task_config.get_multi(
            db, skip=skip, limit=page_size, filters=filters
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return NlsqlTaskConfigPaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )

    async def get_all_with_pagination_and_relations(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> NlsqlTaskConfigPaginatedWithRelationsResponse:
        # 获取基础数据
        skip = (page - 1) * page_size
        total = await crud_nlsql_task_config.get_count(db, filters=filters)
        items = await crud_nlsql_task_config.get_multi(
            db, skip=skip, limit=page_size, filters=filters
        )

        # 获取关联信息
        result = []
        for item in items:
            # 获取LLM配置名称
            llm_config = await crud_llm_config.get(db, id=item.llm_config_id)
            llm_config_name = llm_config.provider if llm_config else None

            # 获取数据库配置名称
            db_config = await crud_db_config.get(db, id=item.db_config_id)
            db_config_name = db_config.database_name if db_config else None

            # 获取用户提示词配置名称
            user_prompt_config = await crud_user_prompt_config.get(db, id=item.user_prompt_config_id)
            user_prompt_config_name = user_prompt_config.config_name if user_prompt_config else None

            # 构建带关联信息的对象
            item_dict = item.__dict__.copy()
            item_dict['llm_config_name'] = llm_config_name
            item_dict['db_config_name'] = db_config_name
            item_dict['user_prompt_config_name'] = user_prompt_config_name

            result.append(NlsqlTaskConfigWithRelations(**item_dict))

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return NlsqlTaskConfigPaginatedWithRelationsResponse(
            items=result,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )

    async def search(
        self,
        db: AsyncSession,
        *,
        keyword: Optional[str] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> NlsqlTaskConfigPaginatedResponse:
        skip = (page - 1) * page_size
        total = await crud_nlsql_task_config.search_count(
            db, keyword=keyword, status=status
        )
        items = await crud_nlsql_task_config.search(
            db, keyword=keyword, status=status, skip=skip, limit=page_size
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return NlsqlTaskConfigPaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> NlsqlTaskConfig:
        # 验证关联的外键是否存在
        llm_config = await crud_llm_config.get(db, id=obj_in.get('llm_config_id'))
        if not llm_config:
            raise HTTPException(status_code=404, detail=f"LLM配置ID {obj_in.get('llm_config_id')} 不存在")

        db_config = await crud_db_config.get(db, id=obj_in.get('db_config_id'))
        if not db_config:
            raise HTTPException(status_code=404, detail=f"数据库配置ID {obj_in.get('db_config_id')} 不存在")

        user_prompt_config = await crud_user_prompt_config.get(db, id=obj_in.get('user_prompt_config_id'))
        if not user_prompt_config:
            raise HTTPException(status_code=404, detail=f"用户提示词配置ID {obj_in.get('user_prompt_config_id')} 不存在")

        return await crud_nlsql_task_config.create(db, obj_in=obj_in)

    async def update(
        self,
        db: AsyncSession,
        *,
        id: int,
        obj_in: Dict[str, Any]
    ) -> NlsqlTaskConfig:
        db_obj = await crud_nlsql_task_config.get(db, id=id)
        if not db_obj:
            raise HTTPException(status_code=404, detail=f"任务配置ID {id} 不存在")

        # 如果更新了外键，需要验证新的外键是否存在
        if 'llm_config_id' in obj_in:
            llm_config = await crud_llm_config.get(db, id=obj_in['llm_config_id'])
            if not llm_config:
                raise HTTPException(status_code=404, detail=f"LLM配置ID {obj_in['llm_config_id']} 不存在")

        if 'db_config_id' in obj_in:
            db_config = await crud_db_config.get(db, id=obj_in['db_config_id'])
            if not db_config:
                raise HTTPException(status_code=404, detail=f"数据库配置ID {obj_in['db_config_id']} 不存在")

        if 'user_prompt_config_id' in obj_in:
            user_prompt_config = await crud_user_prompt_config.get(db, id=obj_in['user_prompt_config_id'])
            if not user_prompt_config:
                raise HTTPException(status_code=404, detail=f"用户提示词配置ID {obj_in['user_prompt_config_id']} 不存在")

        return await crud_nlsql_task_config.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, *, id: int) -> NlsqlTaskConfig:
        db_obj = await crud_nlsql_task_config.get(db, id=id)
        if not db_obj:
            raise HTTPException(status_code=404, detail=f"任务配置ID {id} 不存在")
        return await crud_nlsql_task_config.delete(db, id=id)

    async def delete_multiple(self, db: AsyncSession, *, ids: List[int]) -> int:
        # 验证所有ID是否存在
        existing_ids = []
        for id in ids:
            db_obj = await crud_nlsql_task_config.get(db, id=id)
            if db_obj:
                existing_ids.append(id)

        if not existing_ids:
            raise HTTPException(status_code=404, detail="没有找到要删除的任务配置")

        return await crud_nlsql_task_config.delete_multiple(db, ids=existing_ids)


nlsql_task_config_service = NlsqlTaskConfigService()
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.db_config import crud_db_config
from app.models.db_config import DbConfig


class DbConfigService:
    async def get_by_id(self, db: AsyncSession, id: int) -> Optional[DbConfig]:
        return await crud_db_config.get(db, id=id)

    async def get_all_with_pagination(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        skip = (page - 1) * page_size

        items = await crud_db_config.get_multi(
            db=db,
            skip=skip,
            limit=page_size,
            filters=filters
        )

        total = await crud_db_config.get_count(db=db, filters=filters)

        total_pages = (total + page_size - 1) // page_size

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> DbConfig:
        # 移除IP+端口唯一性限制，允许重复配置
        return await crud_db_config.create(db=db, obj_in=obj_in)

    async def update(
        self,
        db: AsyncSession,
        *,
        id: int,
        obj_in: Dict[str, Any]
    ) -> Optional[DbConfig]:
        db_obj = await crud_db_config.get(db, id=id)
        if not db_obj:
            return None

        # 移除IP+端口唯一性限制，允许更新为重复的IP:端口配置
        return await crud_db_config.update(db=db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[DbConfig]:
        return await crud_db_config.delete(db, id=id)

    async def delete_multiple(self, db: AsyncSession, *, ids: List[int]) -> int:
        return await crud_db_config.delete_multiple(db, ids=ids)

    async def search(
        self,
        db: AsyncSession,
        *,
        keyword: Optional[str] = None,
        type_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        filters = {}

        if keyword:
            filters["ip"] = keyword
            filters["username"] = keyword

        if type_filter:
            filters["type"] = type_filter

        return await self.get_all_with_pagination(
            db=db,
            page=page,
            page_size=page_size,
            filters=filters
        )


db_config_service = DbConfigService()
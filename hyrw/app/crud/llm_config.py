from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from app.models.llm_config import LlmConfig


class CRUDLlmConfig:
    def __init__(self):
        self.model = LlmConfig

    async def get(self, db: AsyncSession, id: int) -> Optional[LlmConfig]:
        """根据ID获取单条记录"""
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LlmConfig]:
        """根据条件获取多条记录"""
        query = select(self.model)

        if filters:
            conditions = []
            if filters.get('provider'):
                conditions.append(self.model.provider.like(f"%{filters['provider']}%"))
            if filters.get('status'):
                conditions.append(self.model.status == filters['status'])

            if conditions:
                query = query.where(and_(*conditions))

        result = await db.execute(query)
        return result.scalars().all()

    async def get_multi_with_pagination(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """分页查询"""
        query = select(self.model)
        count_query = select(func.count(self.model.id))

        # 构建查询条件
        if filters:
            conditions = []
            if filters.get('provider'):
                conditions.append(self.model.provider.like(f"%{filters['provider']}%"))
            if filters.get('status'):
                conditions.append(self.model.status == filters['status'])

            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))

        # 获取总数
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # 分页查询
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await db.execute(query)
        items = result.scalars().all()

        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size
        }

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> LlmConfig:
        """创建新记录"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: LlmConfig,
        obj_in: Dict[str, Any]
    ) -> LlmConfig:
        """更新记录"""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[LlmConfig]:
        """删除单条记录"""
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def delete_multi(self, db: AsyncSession, *, ids: List[int]) -> Dict[str, Any]:
        """批量删除"""
        # 查询要删除的记录
        result = await db.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        objs = result.scalars().all()

        if not objs:
            return {'deleted_count': 0, 'deleted_ids': []}

        # 批量删除
        await db.execute(
            delete(self.model).where(self.model.id.in_(ids))
        )
        await db.commit()

        return {
            'deleted_count': len(objs),
            'deleted_ids': [obj.id for obj in objs]
        }

    async def exists(self, db: AsyncSession, *, id: int) -> bool:
        """检查记录是否存在"""
        result = await db.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None

    async def get_by_provider(
        self,
        db: AsyncSession,
        *,
        provider: str
    ) -> List[LlmConfig]:
        """根据供应商获取记录"""
        result = await db.execute(
            select(self.model).where(self.model.provider == provider)
        )
        return result.scalars().all()


crud_llm_config = CRUDLlmConfig()
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func, or_
from app.models.nlsql_task_config import NlsqlTaskConfig


class CRUdnlsql_task_config:
    def __init__(self):
        self.model = NlsqlTaskConfig

    async def get(self, db: AsyncSession, id: int) -> Optional[NlsqlTaskConfig]:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[NlsqlTaskConfig]:
        query = select(self.model)

        if filters:
            conditions = []

            if 'status' in filters and filters['status'] is not None:
                conditions.append(self.model.status == filters['status'])

            if 'llm_config_id' in filters and filters['llm_config_id'] is not None:
                conditions.append(self.model.llm_config_id == filters['llm_config_id'])

            if 'db_config_id' in filters and filters['db_config_id'] is not None:
                conditions.append(self.model.db_config_id == filters['db_config_id'])

            if 'user_prompt_config_id' in filters and filters['user_prompt_config_id'] is not None:
                conditions.append(self.model.user_prompt_config_id == filters['user_prompt_config_id'])

            if 'description' in filters and filters['description']:
                conditions.append(self.model.description.ilike(f"%{filters['description']}%"))

            if conditions:
                query = query.where(and_(*conditions))

        query = query.offset(skip).limit(limit).order_by(self.model.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()

    async def get_count(
        self,
        db: AsyncSession,
        *,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        query = select(func.count(self.model.id))

        if filters:
            conditions = []

            if 'status' in filters and filters['status'] is not None:
                conditions.append(self.model.status == filters['status'])

            if 'llm_config_id' in filters and filters['llm_config_id'] is not None:
                conditions.append(self.model.llm_config_id == filters['llm_config_id'])

            if 'db_config_id' in filters and filters['db_config_id'] is not None:
                conditions.append(self.model.db_config_id == filters['db_config_id'])

            if 'user_prompt_config_id' in filters and filters['user_prompt_config_id'] is not None:
                conditions.append(self.model.user_prompt_config_id == filters['user_prompt_config_id'])

            if 'description' in filters and filters['description']:
                conditions.append(self.model.description.ilike(f"%{filters['description']}%"))

            if conditions:
                query = query.where(and_(*conditions))

        result = await db.execute(query)
        return result.scalar()

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> NlsqlTaskConfig:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: NlsqlTaskConfig,
        obj_in: Dict[str, Any]
    ) -> NlsqlTaskConfig:
        for field in obj_in:
            if hasattr(db_obj, field):
                setattr(db_obj, field, obj_in[field])

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[NlsqlTaskConfig]:
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def delete_multiple(self, db: AsyncSession, *, ids: List[int]) -> int:
        query = delete(self.model).where(self.model.id.in_(ids))
        result = await db.execute(query)
        await db.commit()
        return result.rowcount

    async def search(
        self,
        db: AsyncSession,
        *,
        keyword: Optional[str] = None,
        status: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[NlsqlTaskConfig]:
        query = select(self.model)
        conditions = []

        if keyword:
            conditions.append(
                or_(
                    self.model.description.ilike(f"%{keyword}%"),
                )
            )

        if status is not None:
            conditions.append(self.model.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.offset(skip).limit(limit).order_by(self.model.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()

    async def search_count(
        self,
        db: AsyncSession,
        *,
        keyword: Optional[str] = None,
        status: Optional[int] = None
    ) -> int:
        query = select(func.count(self.model.id))
        conditions = []

        if keyword:
            conditions.append(
                or_(
                    self.model.description.ilike(f"%{keyword}%"),
                )
            )

        if status is not None:
            conditions.append(self.model.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        result = await db.execute(query)
        return result.scalar()

    async def get_by_llm_config_id(self, db: AsyncSession, llm_config_id: int) -> List[NlsqlTaskConfig]:
        result = await db.execute(
            select(self.model).where(self.model.llm_config_id == llm_config_id)
        )
        return result.scalars().all()

    async def get_by_db_config_id(self, db: AsyncSession, db_config_id: int) -> List[NlsqlTaskConfig]:
        result = await db.execute(
            select(self.model).where(self.model.db_config_id == db_config_id)
        )
        return result.scalars().all()

    async def get_by_user_prompt_config_id(self, db: AsyncSession, user_prompt_config_id: int) -> List[NlsqlTaskConfig]:
        result = await db.execute(
            select(self.model).where(self.model.user_prompt_config_id == user_prompt_config_id)
        )
        return result.scalars().all()


crud_nlsql_task_config = CRUdnlsql_task_config()
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from app.models.db_config import DbConfig


class CRUDbConfig:
    def __init__(self):
        self.model = DbConfig

    async def get(self, db: AsyncSession, id: int) -> Optional[DbConfig]:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[DbConfig]:
        query = select(self.model)

        if filters:
            conditions = []

            if 'type' in filters and filters['type']:
                conditions.append(self.model.type.ilike(f"%{filters['type']}%"))

            if 'database_name' in filters and filters['database_name']:
                conditions.append(self.model.database_name.ilike(f"%{filters['database_name']}%"))

            if 'ip' in filters and filters['ip']:
                conditions.append(self.model.ip.ilike(f"%{filters['ip']}%"))

            if 'port' in filters and filters['port'] is not None:
                conditions.append(self.model.port == filters['port'])

            if 'username' in filters and filters['username']:
                conditions.append(self.model.username.ilike(f"%{filters['username']}%"))

            if 'schema_name' in filters and filters['schema_name']:
                conditions.append(self.model.schema_name.ilike(f"%{filters['schema_name']}%"))

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

            if 'type' in filters and filters['type']:
                conditions.append(self.model.type.ilike(f"%{filters['type']}%"))

            if 'database_name' in filters and filters['database_name']:
                conditions.append(self.model.database_name.ilike(f"%{filters['database_name']}%"))

            if 'ip' in filters and filters['ip']:
                conditions.append(self.model.ip.ilike(f"%{filters['ip']}%"))

            if 'port' in filters and filters['port'] is not None:
                conditions.append(self.model.port == filters['port'])

            if 'username' in filters and filters['username']:
                conditions.append(self.model.username.ilike(f"%{filters['username']}%"))

            if 'schema_name' in filters and filters['schema_name']:
                conditions.append(self.model.schema_name.ilike(f"%{filters['schema_name']}%"))

            if conditions:
                query = query.where(and_(*conditions))

        result = await db.execute(query)
        return result.scalar()

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> DbConfig:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: DbConfig,
        obj_in: Dict[str, Any]
    ) -> DbConfig:
        for field in obj_in:
            if hasattr(db_obj, field):
                setattr(db_obj, field, obj_in[field])

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[DbConfig]:
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

    async def get_by_ip_and_port(
        self,
        db: AsyncSession,
        *,
        ip: str,
        port: int
    ) -> Optional[DbConfig]:
        result = await db.execute(
            select(self.model).where(
                and_(self.model.ip == ip, self.model.port == port)
            )
        )
        return result.scalar_one_or_none()


crud_db_config = CRUDbConfig()
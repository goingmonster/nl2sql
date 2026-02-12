from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from sqlalchemy.orm import selectinload
from app.models.table_metadata_extended import TableMetadataBasic, TableSampleData, TableFieldMetadata


class CRUDTableMetadataBasic:
    def __init__(self):
        self.model = TableMetadataBasic

    async def get(self, db: AsyncSession, id: int) -> Optional[TableMetadataBasic]:
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.table_sample_data))
            .options(selectinload(self.model.table_field_metadata))
            .where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_task_id(self, db: AsyncSession, task_id: int) -> List[TableMetadataBasic]:
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.table_sample_data))
            .options(selectinload(self.model.table_field_metadata))
            .where(self.model.table_task_id == task_id)
        )
        return list(result.unique().scalars().all())

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[TableMetadataBasic]:
        result = await db.execute(
            select(self.model)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> TableMetadataBasic:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: TableMetadataBasic,
        obj_in: Dict[str, Any]
    ) -> TableMetadataBasic:
        for field in obj_in:
            if hasattr(db_obj, field):
                setattr(db_obj, field, obj_in[field])

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[TableMetadataBasic]:
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj


class CRUDTableSampleData:
    def __init__(self):
        self.model = TableSampleData

    async def get(self, db: AsyncSession, id: int) -> Optional[TableSampleData]:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_by_table_metadata_id(self, db: AsyncSession, table_metadata_id: int) -> Optional[TableSampleData]:
        result = await db.execute(
            select(self.model).where(self.model.table_metadata_id == table_metadata_id)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> TableSampleData:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: TableSampleData,
        obj_in: Dict[str, Any]
    ) -> TableSampleData:
        for field in obj_in:
            if hasattr(db_obj, field):
                setattr(db_obj, field, obj_in[field])

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[TableSampleData]:
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj


class CRUDTableFieldMetadata:
    def __init__(self):
        self.model = TableFieldMetadata

    async def get(self, db: AsyncSession, id: int) -> Optional[TableFieldMetadata]:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_by_table_metadata_id(
        self, db: AsyncSession, table_metadata_id: int
    ) -> List[TableFieldMetadata]:
        result = await db.execute(
            select(self.model).where(self.model.table_metadata_id == table_metadata_id)
        )
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> TableFieldMetadata:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def create_multi(
        self, db: AsyncSession, *, objs_in: List[Dict[str, Any]]
    ) -> List[TableFieldMetadata]:
        db_objs = [self.model(**obj_in) for obj_in in objs_in]
        db.add_all(db_objs)
        await db.commit()
        for obj in db_objs:
            await db.refresh(obj)
        return db_objs

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: TableFieldMetadata,
        obj_in: Dict[str, Any]
    ) -> TableFieldMetadata:
        for field in obj_in:
            if hasattr(db_obj, field):
                setattr(db_obj, field, obj_in[field])

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[TableFieldMetadata]:
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj


crud_table_metadata_basic = CRUDTableMetadataBasic()
crud_table_sample_data = CRUDTableSampleData()
crud_table_field_metadata = CRUDTableFieldMetadata()

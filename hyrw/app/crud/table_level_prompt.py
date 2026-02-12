from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from app.models.table_level_prompt import TableLevelPrompt


class CRUDTableLevelPrompt:
    def __init__(self):
        self.model = TableLevelPrompt

    async def get(self, db: AsyncSession, id: int) -> Optional[TableLevelPrompt]:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi_with_pagination(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        table_name: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> Dict[str, Any]:
        query = select(self.model)
        count_query = select(func.count(self.model.id))

        conditions = []
        if table_name:
            conditions.append(self.model.table_name.ilike(f"%{table_name}%"))
        if task_id is not None:
            conditions.append(self.model.task_id == task_id)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await db.execute(
            query.offset(offset).limit(page_size).order_by(self.model.created_at.desc())
        )
        items = result.scalars().all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> TableLevelPrompt:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: TableLevelPrompt,
        obj_in: Dict[str, Any]
    ) -> TableLevelPrompt:
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[TableLevelPrompt]:
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def delete_multi(self, db: AsyncSession, *, ids: List[int]) -> Dict[str, Any]:
        result = await db.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        objs = result.scalars().all()

        if not objs:
            return {"deleted_count": 0, "deleted_ids": []}

        await db.execute(delete(self.model).where(self.model.id.in_(ids)))
        await db.commit()

        return {
            "deleted_count": len(objs),
            "deleted_ids": [obj.id for obj in objs]
        }


crud_table_level_prompt = CRUDTableLevelPrompt()

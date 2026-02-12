from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.table_metadata import TableMetadata
from app.models.table_metadata_extended import TableSampleData, TableFieldMetadata
from app.schemas.table_metadata import TableMetadataCreate, TableMetadataUpdate


class CRUDTableMetadata:
    async def get(self, db: AsyncSession, id: int) -> Optional[TableMetadata]:
        """获取单个表元数据记录"""
        result = await db.execute(select(TableMetadata).filter(TableMetadata.id == id))
        return result.scalar_one_or_none()

    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        conditions: Optional[Dict[str, Any]] = None,
        table_name: Optional[str] = None,
        table_type: Optional[str] = None,
        min_row_count: Optional[int] = None,
        max_row_count: Optional[int] = None,
        db_config_ids: Optional[List[int]] = None,
        order_by: Optional[str] = "created_at",
        order_direction: Optional[str] = "desc",
        skip: int = 0,
        limit: int = 100
    ) -> List[TableMetadata]:
        """带条件查询的获取多个表元数据记录"""
        query = select(TableMetadata)

        # 处理条件查询
        if conditions:
            for key, value in conditions.items():
                if hasattr(TableMetadata, key):
                    if isinstance(value, list):
                        query = query.filter(getattr(TableMetadata, key).in_(value))
                    else:
                        query = query.filter(getattr(TableMetadata, key) == value)

        # 单独条件查询
        if table_name:
            query = query.filter(TableMetadata.table_name.ilike(f"%{table_name}%"))

        if table_type:
            query = query.filter(TableMetadata.table_type == table_type)

        if min_row_count is not None:
            query = query.filter(TableMetadata.table_row_count >= min_row_count)

        if max_row_count is not None:
            query = query.filter(TableMetadata.table_row_count <= max_row_count)

        if db_config_ids:
            query = query.filter(TableMetadata.db_config_id.in_(db_config_ids))

        # 排序
        if order_by and hasattr(TableMetadata, order_by):
            order_column = getattr(TableMetadata, order_by)
            if order_direction.lower() == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_count_with_filters(
        self,
        db: AsyncSession,
        conditions: Optional[Dict[str, Any]] = None,
        table_name: Optional[str] = None,
        table_type: Optional[str] = None,
        min_row_count: Optional[int] = None,
        max_row_count: Optional[int] = None,
        db_config_ids: Optional[List[int]] = None
    ) -> int:
        """带条件查询获取记录总数"""
        query = select(func.count(TableMetadata.id))

        # 处理条件查询
        if conditions:
            for key, value in conditions.items():
                if hasattr(TableMetadata, key):
                    if isinstance(value, list):
                        query = query.filter(getattr(TableMetadata, key).in_(value))
                    else:
                        query = query.filter(getattr(TableMetadata, key) == value)

        # 单独条件查询
        if table_name:
            query = query.filter(TableMetadata.table_name.ilike(f"%{table_name}%"))

        if table_type:
            query = query.filter(TableMetadata.table_type == table_type)

        if min_row_count is not None:
            query = query.filter(TableMetadata.table_row_count >= min_row_count)

        if max_row_count is not None:
            query = query.filter(TableMetadata.table_row_count <= max_row_count)

        if db_config_ids:
            query = query.filter(TableMetadata.db_config_id.in_(db_config_ids))

        result = await db.execute(query)
        return result.scalar()

    async def get_multi(
        self,
        db: AsyncSession,
        db_config_id: Optional[int] = None,
        table_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TableMetadata]:
        """获取多个表元数据记录（简化版）"""
        query = select(TableMetadata)

        if db_config_id is not None:
            query = query.filter(TableMetadata.db_config_id == db_config_id)

        if table_name:
            query = query.filter(TableMetadata.table_name.ilike(f"%{table_name}%"))

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_count(
        self,
        db: AsyncSession,
        db_config_id: Optional[int] = None,
        table_name: Optional[str] = None
    ) -> int:
        """获取记录总数（简化版）"""
        query = select(func.count(TableMetadata.id))

        if db_config_id is not None:
            query = query.filter(TableMetadata.db_config_id == db_config_id)

        if table_name:
            query = query.filter(TableMetadata.table_name.ilike(f"%{table_name}%"))

        result = await db.execute(query)
        return result.scalar()

    async def get_by_db_config_and_table(
        self,
        db: AsyncSession,
        db_config_id: int,
        table_name: str
    ) -> Optional[TableMetadata]:
        """根据db_config_id和table_name获取记录"""
        result = await db.execute(
            select(TableMetadata)
            .filter(TableMetadata.db_config_id == db_config_id)
            .filter(TableMetadata.table_name == table_name)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, obj_in: TableMetadataCreate) -> TableMetadata:
        """创建表元数据记录"""
        db_obj = TableMetadata(**obj_in.dict())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: TableMetadata,
        obj_in: TableMetadataUpdate
    ) -> TableMetadata:
        """更新表元数据记录"""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, id: int) -> Optional[TableMetadata]:
        """删除表元数据记录（级联删除样例数据和字段元数据）"""
        obj = await self.get(db, id)
        if obj:
            # 先删除相关的样例数据
            await db.execute(delete(TableSampleData).filter(TableSampleData.table_metadata_id == id))
            # 再删除相关的字段元数据
            await db.execute(delete(TableFieldMetadata).filter(TableFieldMetadata.table_metadata_id == id))
            # 最后删除表元数据
            await db.execute(delete(TableMetadata).filter(TableMetadata.id == id))
            await db.commit()
        return obj

    async def delete_batch(self, db: AsyncSession, ids: List[int]) -> List[TableMetadata]:
        """批量删除表元数据记录（级联删除样例数据和字段元数据）"""
        # 先获取要删除的表元数据记录
        query = select(TableMetadata).filter(TableMetadata.id.in_(ids))
        result = await db.execute(query)
        records = result.scalars().all()

        if records:
            # 先删除所有相关的样例数据
            await db.execute(delete(TableSampleData).filter(TableSampleData.table_metadata_id.in_(ids)))
            # 再删除所有相关的字段元数据
            await db.execute(delete(TableFieldMetadata).filter(TableFieldMetadata.table_metadata_id.in_(ids)))
            # 最后删除表元数据
            await db.execute(delete(TableMetadata).filter(TableMetadata.id.in_(ids)))
            await db.commit()

        return records

    async def delete_by_db_config_id(self, db: AsyncSession, db_config_id: int):
        """根据db_config_id删除所有相关记录"""
        await db.execute(delete(TableMetadata).filter(TableMetadata.db_config_id == db_config_id))
        await db.commit()

    async def delete_multiple(self, db: AsyncSession, ids: List[int]) -> List[TableMetadata]:
        """批量删除表元数据记录（级联删除相关的样例数据和字段元数据）"""
        # 先获取要删除的记录
        query = select(TableMetadata).filter(TableMetadata.id.in_(ids))
        result = await db.execute(query)
        records = result.scalars().all()

        if records:
            # 获取相关的表ID列表
            table_ids = [record.id for record in records]

            # 先删除相关的样例数据
            await db.execute(delete(TableSampleData).filter(TableSampleData.table_metadata_id.in_(table_ids)))

            # 再删除相关的字段元数据
            await db.execute(delete(TableFieldMetadata).filter(TableFieldMetadata.table_metadata_id.in_(table_ids)))

            # 最后删除表元数据
            await db.execute(delete(TableMetadata).filter(TableMetadata.id.in_(ids)))
            await db.commit()

        return records

    async def delete_by_conditions(
        self,
        db: AsyncSession,
        conditions: Dict[str, Any]
    ) -> List[TableMetadata]:
        """根据条件批量删除表元数据记录（级联删除相关的样例数据和字段元数据）"""
        # 先获取要删除的记录
        query = select(TableMetadata)
        for key, value in conditions.items():
            if hasattr(TableMetadata, key):
                if isinstance(value, list):
                    query = query.filter(getattr(TableMetadata, key).in_(value))
                else:
                    query = query.filter(getattr(TableMetadata, key) == value)

        result = await db.execute(query)
        records = result.scalars().all()

        if records:
            # 获取相关的表ID列表
            table_ids = [record.id for record in records]

            # 先删除相关的样例数据
            await db.execute(delete(TableSampleData).filter(TableSampleData.table_metadata_id.in_(table_ids)))

            # 再删除相关的字段元数据
            await db.execute(delete(TableFieldMetadata).filter(TableFieldMetadata.table_metadata_id.in_(table_ids)))

            # 最后删除表元数据
            delete_query = delete(TableMetadata)
            for key, value in conditions.items():
                if hasattr(TableMetadata, key):
                    if isinstance(value, list):
                        delete_query = delete_query.filter(getattr(TableMetadata, key).in_(value))
                    else:
                        delete_query = delete_query.filter(getattr(TableMetadata, key) == value)

            await db.execute(delete_query)
            await db.commit()

        return records

    async def bulk_create_or_update(
        self,
        db: AsyncSession,
        table_list: List[dict],
        db_config_id: int
    ) -> List[TableMetadata]:
        """批量创建或更新表元数据记录"""
        result = []
        for table_data in table_list:
            # 检查是否已存在
            existing = await self.get_by_db_config_and_table(
                db,
                db_config_id,
                table_data['table_name']
            )

            if existing:
                # 更新现有记录
                update_data = TableMetadataUpdate(**table_data)
                updated = await self.update(db, existing, update_data)
                result.append(updated)
            else:
                # 创建新记录
                table_data['db_config_id'] = db_config_id
                create_data = TableMetadataCreate(**table_data)
                created = await self.create(db, create_data)
                result.append(created)

        return result


crud_table_metadata = CRUDTableMetadata()
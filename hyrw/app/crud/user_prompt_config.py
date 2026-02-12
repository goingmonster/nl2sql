from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select, func, delete
from app.models.user_prompt_config import UserPromptConfig
from app.schemas.user_prompt_config import UserPromptConfigCreate, UserPromptConfigUpdate
import json


class CRUDUserPromptConfig:
    """用户提示词配置CRUD操作（异步版本）"""

    async def get(self, db: AsyncSession, id: int) -> Optional[UserPromptConfig]:
        """获取单个用户提示词配置"""
        result = await db.execute(
            select(UserPromptConfig).filter(UserPromptConfig.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, db: AsyncSession, config_name: str) -> Optional[UserPromptConfig]:
        """根据配置名称获取用户提示词配置"""
        result = await db.execute(
            select(UserPromptConfig).filter(UserPromptConfig.config_name == config_name)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        config_name: Optional[str] = None,
        config_type: Optional[int] = None
    ) -> List[UserPromptConfig]:
        """获取多个用户提示词配置（支持分页和过滤）"""
        query = select(UserPromptConfig)

        conditions = []
        if config_name:
            conditions.append(UserPromptConfig.config_name.contains(config_name))

        if config_type is not None:
            conditions.append(UserPromptConfig.config_type == config_type)

        if conditions:
            query = query.filter(and_(*conditions))

        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def count(
        self,
        db: AsyncSession,
        *,
        config_name: Optional[str] = None,
        config_type: Optional[int] = None
    ) -> int:
        """统计用户提示词配置数量"""
        query = select(func.count(UserPromptConfig.id))

        conditions = []
        if config_name:
            conditions.append(UserPromptConfig.config_name.contains(config_name))

        if config_type is not None:
            conditions.append(UserPromptConfig.config_type == config_type)

        if conditions:
            query = query.filter(and_(*conditions))

        result = await db.execute(query)
        return result.scalar()

    async def create(self, db: AsyncSession, *, obj_in: UserPromptConfigCreate) -> UserPromptConfig:
        """创建用户提示词配置"""
        db_obj = UserPromptConfig(
            config_name=obj_in.config_name,
            system_config=obj_in.system_config,
            table_notes=json.dumps(obj_in.table_notes, ensure_ascii=False) if obj_in.table_notes else None,
            field_notes=json.dumps(obj_in.field_notes, ensure_ascii=False) if obj_in.field_notes else None,
            config_type=obj_in.config_type
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: UserPromptConfig,
        obj_in: UserPromptConfigUpdate
    ) -> UserPromptConfig:
        """更新用户提示词配置"""
        update_data = obj_in.model_dump(exclude_unset=True)

        # 处理JSON字段
        if "table_notes" in update_data:
            update_data["table_notes"] = json.dumps(update_data["table_notes"], ensure_ascii=False) if update_data["table_notes"] else None

        if "field_notes" in update_data:
            update_data["field_notes"] = json.dumps(update_data["field_notes"], ensure_ascii=False) if update_data["field_notes"] else None

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[UserPromptConfig]:
        """删除单个用户提示词配置"""
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def delete_batch(self, db: AsyncSession, *, ids: List[int]) -> List[UserPromptConfig]:
        """批量删除用户提示词配置"""
        # 先获取要删除的对象
        result = await db.execute(
            select(UserPromptConfig).filter(UserPromptConfig.id.in_(ids))
        )
        objs = result.scalars().all()

        if objs:
            # 删除对象
            await db.execute(
                delete(UserPromptConfig).filter(UserPromptConfig.id.in_(ids))
            )
            await db.commit()

        return objs


# 创建CRUD实例
crud_user_prompt_config = CRUDUserPromptConfig()
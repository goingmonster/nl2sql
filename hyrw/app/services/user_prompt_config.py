from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.crud.user_prompt_config import crud_user_prompt_config
from app.models.user_prompt_config import UserPromptConfig
from app.schemas.user_prompt_config import (
    UserPromptConfigCreate,
    UserPromptConfigUpdate,
    UserPromptConfigInDB
)
import json


class UserPromptConfigService:
    """用户提示词配置业务逻辑层（异步版本）"""

    def __init__(self):
        self.crud = crud_user_prompt_config

    async def get_by_id(self, db: AsyncSession, id: int) -> UserPromptConfigInDB:
        """根据ID获取用户提示词配置"""
        config = await self.crud.get(db, id=id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户提示词配置 ID {id} 不存在"
            )
        return self._convert_to_schema(config)

    async def get_by_name(self, db: AsyncSession, config_name: str) -> UserPromptConfigInDB:
        """根据配置名称获取用户提示词配置"""
        config = await self.crud.get_by_name(db, config_name=config_name)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户提示词配置名称 {config_name} 不存在"
            )
        return self._convert_to_schema(config)

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        config_name: Optional[str] = None,
        config_type: Optional[int] = None
    ) -> Tuple[List[UserPromptConfigInDB], int]:
        """获取用户提示词配置列表（支持分页和过滤）"""
        configs = await self.crud.get_multi(
            db, skip=skip, limit=limit, config_name=config_name, config_type=config_type
        )
        total = await self.crud.count(db, config_name=config_name, config_type=config_type)

        converted_configs = [self._convert_to_schema(config) for config in configs]
        return converted_configs, total

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: UserPromptConfigCreate
    ) -> UserPromptConfigInDB:
        """创建用户提示词配置"""
        # 检查配置名称是否已存在
        existing_config = await self.crud.get_by_name(db, config_name=obj_in.config_name)
        if existing_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"配置名称 '{obj_in.config_name}' 已存在"
            )

        # 验证配置类型
        if obj_in.config_type not in [1, 2, 3]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="配置类型必须是 1-默认，2-自定义，3-系统预制"
            )

        config = await self.crud.create(db, obj_in=obj_in)
        return self._convert_to_schema(config)

    async def update(
        self,
        db: AsyncSession,
        *,
        id: int,
        obj_in: UserPromptConfigUpdate
    ) -> UserPromptConfigInDB:
        """更新用户提示词配置"""
        db_config = await self.crud.get(db, id=id)
        if not db_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户提示词配置 ID {id} 不存在"
            )

        # 如果更新配置名称，检查是否已存在
        if obj_in.config_name and obj_in.config_name != db_config.config_name:
            existing_config = await self.crud.get_by_name(db, config_name=obj_in.config_name)
            if existing_config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"配置名称 '{obj_in.config_name}' 已存在"
                )

        # 验证配置类型
        if obj_in.config_type and obj_in.config_type not in [1, 2, 3]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="配置类型必须是 1-默认，2-自定义，3-系统预制"
            )

        config = await self.crud.update(db, db_obj=db_config, obj_in=obj_in)
        return self._convert_to_schema(config)

    async def delete(self, db: AsyncSession, *, id: int) -> UserPromptConfigInDB:
        """删除用户提示词配置"""
        config = await self.crud.get(db, id=id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"用户提示词配置 ID {id} 不存在"
            )

        deleted_config = await self.crud.delete(db, id=id)
        return self._convert_to_schema(deleted_config)

    async def delete_batch(self, db: AsyncSession, *, ids: List[int]) -> List[UserPromptConfigInDB]:
        """批量删除用户提示词配置"""
        if not ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="删除ID列表不能为空"
            )

        deleted_configs = await self.crud.delete_batch(db, ids=ids)
        if not deleted_configs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到要删除的配置"
            )

        return [self._convert_to_schema(config) for config in deleted_configs]

    async def get_by_type(self, db: AsyncSession, config_type: int) -> List[UserPromptConfigInDB]:
        """根据配置类型获取用户提示词配置"""
        if config_type not in [1, 2, 3]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="配置类型必须是 1-默认，2-自定义，3-系统预制"
            )

        configs = await self.crud.get_multi(db, config_type=config_type, limit=1000)
        return [self._convert_to_schema(config) for config in configs]

    def _convert_to_schema(self, config: UserPromptConfig) -> UserPromptConfigInDB:
        """将数据库模型转换为Schema对象，处理JSON字段"""
        table_notes = []
        field_notes = []

        if config.table_notes:
            try:
                table_notes = json.loads(config.table_notes)
            except json.JSONDecodeError:
                table_notes = []

        if config.field_notes:
            try:
                field_notes = json.loads(config.field_notes)
            except json.JSONDecodeError:
                field_notes = []

        return UserPromptConfigInDB(
            id=config.id,
            config_name=config.config_name,
            system_config=config.system_config,
            table_notes=table_notes,
            field_notes=field_notes,
            config_type=config.config_type,
            created_at=config.created_at,
            updated_at=config.updated_at
        )


# 创建Service实例
user_prompt_config_service = UserPromptConfigService()
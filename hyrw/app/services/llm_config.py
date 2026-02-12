from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.llm_config import crud_llm_config
from app.schemas.llm_config import LlmConfigCreate, LlmConfigUpdate
from app.models.llm_config import LlmConfig
from app.core.exceptions import NotFoundError, ValidationError


class LlmConfigService:
    """LLM配置服务类"""

    async def get(self, db: AsyncSession, id: int) -> LlmConfig:
        """获取单个LLM配置"""
        obj = await crud_llm_config.get(db, id=id)
        if not obj:
            raise NotFoundError(f"LLM配置 ID {id} 不存在")
        return obj

    async def get_multi_with_pagination(
        self,
        db: AsyncSession,
        *,
        provider: str = None,
        status: int = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """分页获取LLM配置列表"""
        filters = {}
        if provider:
            filters['provider'] = provider
        if status is not None:
            filters['status'] = status

        return await crud_llm_config.get_multi_with_pagination(
            db, page=page, page_size=page_size, filters=filters
        )

    async def create(self, db: AsyncSession, *, obj_in: LlmConfigCreate) -> LlmConfig:
        """创建新的LLM配置"""
        # 业务逻辑验证
        if obj_in.max_tokens and obj_in.max_tokens < 1:
            raise ValidationError("max_tokens 必须大于 0")

        if obj_in.temperature and (obj_in.temperature < 0 or obj_in.temperature > 2):
            raise ValidationError("temperature 必须在 0-2 之间")

        # 转换为字典
        obj_data = obj_in.model_dump()

        # 调用CRUD层创建
        return await crud_llm_config.create(db, obj_in=obj_data)

    async def update(
        self,
        db: AsyncSession,
        *,
        id: int,
        obj_in: LlmConfigUpdate
    ) -> LlmConfig:
        """更新LLM配置"""
        # 检查对象是否存在
        db_obj = await self.get(db, id)

        # 业务逻辑验证
        if obj_in.max_tokens is not None and obj_in.max_tokens < 1:
            raise ValidationError("max_tokens 必须大于 0")

        if obj_in.temperature is not None and (obj_in.temperature < 0 or obj_in.temperature > 2):
            raise ValidationError("temperature 必须在 0-2 之间")

        # 获取更新数据（过滤None值）
        update_data = obj_in.model_dump(exclude_unset=True)

        # 调用CRUD层更新
        return await crud_llm_config.update(db, db_obj=db_obj, obj_in=update_data)

    async def delete(self, db: AsyncSession, *, id: int) -> LlmConfig:
        """删除单个LLM配置"""
        # 检查对象是否存在
        obj = await self.get(db, id)

        # 调用CRUD层删除
        await crud_llm_config.delete(db, id=id)
        return obj

    async def delete_multi(self, db: AsyncSession, *, ids: List[int]) -> Dict[str, Any]:
        """批量删除LLM配置"""
        if not ids:
            raise ValidationError("删除ID列表不能为空")

        # 检查所有要删除的记录是否存在
        for id in ids:
            await self.get(db, id)

        # 调用CRUD层批量删除
        return await crud_llm_config.delete_multi(db, ids=ids)

    async def get_by_provider(self, db: AsyncSession, *, provider: str) -> List[LlmConfig]:
        """根据供应商获取LLM配置列表"""
        return await crud_llm_config.get_by_provider(db, provider=provider)

    async def enable(self, db: AsyncSession, *, id: int) -> LlmConfig:
        """启用LLM配置"""
        return await self.update(db, id=id, obj_in=LlmConfigUpdate(status=1))

    async def disable(self, db: AsyncSession, *, id: int) -> LlmConfig:
        """禁用LLM配置"""
        return await self.update(db, id=id, obj_in=LlmConfigUpdate(status=2))


# 创建单例实例
llm_config_service = LlmConfigService()
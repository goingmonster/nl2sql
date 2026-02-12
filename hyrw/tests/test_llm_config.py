import pytest
import asyncio
from typing import Generator, AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, Base
from app.crud.llm_config import crud_llm_config
from app.services.llm_config import llm_config_service
from app.schemas.llm_config import LlmConfigCreate, LlmConfigUpdate

# 配置测试数据库
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def sample_llm_config_data():
    return {
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-1234567890abcdef",
        "max_tokens": 4096,
        "temperature": 0.7,
        "description": "OpenAI GPT-4配置",
        "provider": "OpenAI",
        "status": 1
    }


@pytest.fixture
async def sample_llm_config(db_session: AsyncSession, sample_llm_config_data: dict):
    """创建测试用的LLM配置"""
    return await crud_llm_config.create(db_session, obj_in=sample_llm_config_data)


class TestLlmConfigCRUD:
    """CRUD层测试"""

    async def test_create_llm_config(self, db_session: AsyncSession, sample_llm_config_data: dict):
        """测试创建LLM配置"""
        obj = await crud_llm_config.create(db_session, obj_in=sample_llm_config_data)
        assert obj.id is not None
        assert obj.base_url == sample_llm_config_data["base_url"]
        assert obj.api_key == sample_llm_config_data["api_key"]
        assert obj.provider == sample_llm_config_data["provider"]
        assert obj.status == 1

    async def test_get_llm_config(self, db_session: AsyncSession, sample_llm_config):
        """测试获取单个LLM配置"""
        obj = await crud_llm_config.get(db=db_session, id=sample_llm_config.id)
        assert obj is not None
        assert obj.id == sample_llm_config.id
        assert obj.provider == sample_llm_config.provider

    async def test_get_multi_with_pagination(self, db_session: AsyncSession, sample_llm_config_data: dict):
        """测试分页获取LLM配置"""
        # 创建多个配置
        for i in range(5):
            data = sample_llm_config_data.copy()
            data["provider"] = f"provider_{i}"
            await crud_llm_config.create(db_session, obj_in=data)

        # 测试分页
        result = await crud_llm_config.get_multi_with_pagination(db_session, page=1, page_size=3)
        assert len(result["items"]) == 3
        assert result["total"] == 5
        assert result["page"] == 1
        assert result["page_size"] == 3
        assert result["pages"] == 2

    async def test_update_llm_config(self, db_session: AsyncSession, sample_llm_config):
        """测试更新LLM配置"""
        update_data = {
            "max_tokens": 8192,
            "temperature": 0.5,
            "status": 2
        }
        updated_obj = await crud_llm_config.update(db_session, db_obj=sample_llm_config, obj_in=update_data)
        assert updated_obj.max_tokens == 8192
        assert updated_obj.temperature == 0.5
        assert updated_obj.status == 2

    async def test_delete_llm_config(self, db_session: AsyncSession, sample_llm_config):
        """测试删除LLM配置"""
        deleted_obj = await crud_llm_config.delete(db_session, id=sample_llm_config.id)
        assert deleted_obj is not None

        # 验证已删除
        obj = await crud_llm_config.get(db_session, id=sample_llm_config.id)
        assert obj is None

    async def test_delete_multi_llm_config(self, db_session: AsyncSession, sample_llm_config_data: dict):
        """测试批量删除LLM配置"""
        # 创建多个配置
        ids = []
        for i in range(3):
            data = sample_llm_config_data.copy()
            data["provider"] = f"provider_{i}"
            obj = await crud_llm_config.create(db_session, obj_in=data)
            ids.append(obj.id)

        # 批量删除
        result = await crud_llm_config.delete_multi(db_session, ids=ids)
        assert result["deleted_count"] == 3
        assert len(result["deleted_ids"]) == 3

        # 验证已全部删除
        for id in ids:
            assert await crud_llm_config.exists(db_session, id=id) is False

    async def test_get_by_provider(self, db_session: AsyncSession, sample_llm_config):
        """测试根据供应商获取配置"""
        objs = await crud_llm_config.get_by_provider(db_session, provider=sample_llm_config.provider)
        assert len(objs) == 1
        assert objs[0].provider == sample_llm_config.provider


class TestLlmConfigService:
    """Service层测试"""

    async def test_service_create(self, db_session: AsyncSession, sample_llm_config_data: dict):
        """测试Service层创建"""
        obj_in = LlmConfigCreate(**sample_llm_config_data)
        obj = await llm_config_service.create(db_session, obj_in=obj_in)
        assert obj.id is not None
        assert obj.provider == sample_llm_config_data["provider"]

    async def test_service_get_not_found(self, db_session: AsyncSession):
        """测试获取不存在的配置"""
        with pytest.raises(Exception):  # 应该抛出NotFoundError
            await llm_config_service.get(db_session, id=99999)

    async def test_service_update(self, db_session: AsyncSession, sample_llm_config):
        """测试Service层更新"""
        obj_in = LlmConfigUpdate(max_tokens=2048, temperature=0.3)
        updated_obj = await llm_config_service.update(db_session, id=sample_llm_config.id, obj_in=obj_in)
        assert updated_obj.max_tokens == 2048
        assert float(updated_obj.temperature) == 0.3

    async def test_service_enable_disable(self, db_session: AsyncSession, sample_llm_config):
        """测试启用和禁用功能"""
        # 禁用
        disabled_obj = await llm_config_service.disable(db_session, id=sample_llm_config.id)
        assert disabled_obj.status == 2

        # 启用
        enabled_obj = await llm_config_service.enable(db_session, id=sample_llm_config.id)
        assert enabled_obj.status == 1

    async def test_service_validation_error(self, db_session: AsyncSession, sample_llm_config_data: dict):
        """测试验证错误"""
        # 测试创建后更新时的验证
        obj_in = LlmConfigCreate(**sample_llm_config_data)
        obj = await llm_config_service.create(db_session, obj_in=obj_in)

        # 尝试更新为无效的max_tokens
        with pytest.raises(Exception):  # 应该抛出ValidationError
            update_obj_in = LlmConfigUpdate(max_tokens=-1)
            await llm_config_service.update(db_session, id=obj.id, obj_in=update_obj_in)

        # 尝试更新为无效的temperature
        with pytest.raises(Exception):  # 应该抛出ValidationError
            update_obj_in = LlmConfigUpdate(temperature=5.0)  # 超出范围
            await llm_config_service.update(db_session, id=obj.id, obj_in=update_obj_in)


class TestAPI:
    """API层测试"""

    async def test_create_llm_config_api(self, client: AsyncClient, sample_llm_config_data: dict):
        """测试创建API"""
        response = await client.post("/api/v1/llm-config/", json=sample_llm_config_data)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["provider"] == sample_llm_config_data["provider"]

    async def test_get_llm_config_api(self, client: AsyncClient, sample_llm_config):
        """测试获取单个配置API"""
        response = await client.get(f"/api/v1/llm-config/{sample_llm_config.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == sample_llm_config.id

    async def test_get_llm_configs_api(self, client: AsyncClient, sample_llm_config):
        """测试获取配置列表API"""
        response = await client.get("/api/v1/llm-config/")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1

    async def test_update_llm_config_api(self, client: AsyncClient, sample_llm_config):
        """测试更新API"""
        update_data = {"max_tokens": 2048, "status": 2}
        response = await client.put(f"/api/v1/llm-config/{sample_llm_config.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["max_tokens"] == 2048
        assert data["data"]["status"] == 2

    async def test_delete_llm_config_api(self, client: AsyncClient, sample_llm_config):
        """测试删除API"""
        response = await client.delete(f"/api/v1/llm-config/{sample_llm_config.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "删除成功"

    async def test_batch_delete_llm_config_api(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_llm_config_data: dict
    ):
        """测试批量删除API"""
        # 创建多个配置
        ids = []
        for i in range(3):
            data = sample_llm_config_data.copy()
            data["provider"] = f"provider_{i}"
            obj = await crud_llm_config.create(db_session, obj_in=data)
            ids.append(obj.id)

        # 批量删除
        params = {"ids": ids}
        response = await client.delete("/api/v1/llm-config/batch/bulk", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["deleted_count"] == 3

    async def test_get_llm_configs_by_provider_api(self, client: AsyncClient, sample_llm_config):
        """测试根据供应商获取配置API"""
        response = await client.get(f"/api/v1/llm-config/provider/{sample_llm_config.provider}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert data["data"][0]["provider"] == sample_llm_config.provider

    async def test_enable_disable_llm_config_api(self, client: AsyncClient, sample_llm_config):
        """测试启用/禁用API"""
        # 禁用
        response = await client.post(f"/api/v1/llm-config/{sample_llm_config.id}/disable")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == 2

        # 启用
        response = await client.post(f"/api/v1/llm-config/{sample_llm_config.id}/enable")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == 1

    async def test_llm_config_pagination_api(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_llm_config_data: dict
    ):
        """测试分页API"""
        # 创建多个配置
        for i in range(10):
            data = sample_llm_config_data.copy()
            data["provider"] = f"provider_{i}"
            await crud_llm_config.create(db_session, obj_in=data)

        # 测试第一页
        response = await client.get("/api/v1/llm-config/?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["total"] >= 10
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 5

    async def test_llm_config_filter_api(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_llm_config_data: dict
    ):
        """测试过滤API"""
        # 创建不同状态的配置
        data1 = sample_llm_config_data.copy()
        data1["provider"] = "Provider_A"
        data1["status"] = 1
        await crud_llm_config.create(db=db_session, obj_in=data1)

        data2 = sample_llm_config_data.copy()
        data2["provider"] = "Provider_B"
        data2["status"] = 2
        await crud_llm_config.create(db=db_session, obj_in=data2)

        # 测试供应商过滤
        response = await client.get("/api/v1/llm-config/?provider=Provider_A")
        assert response.status_code == 200
        data = response.json()
        assert all(item["provider"] == "Provider_A" for item in data["data"])

        # 测试状态过滤
        response = await client.get("/api/v1/llm-config/?status=2")
        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == 2 for item in data["data"])
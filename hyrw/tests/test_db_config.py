import pytest
import asyncio
from typing import Generator, AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, Base
from app.crud.db_config import crud_db_config
from app.services.db_config import db_config_service


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
async def sample_db_config():
    return {
        "type": "POSTGRESQL",
        "database_name": "test_db",
        "schema_name": "public",
        "ip": "192.168.1.100",
        "port": 5432,
        "username": "postgres",
        "password": "password123"
    }


class TestDbConfigCRUD:
    async def test_create_db_config(self, db_session: AsyncSession, sample_db_config: dict):
        config = await crud_db_config.create(db=db_session, obj_in=sample_db_config)
        assert config.id is not None
        assert config.type == sample_db_config["type"]
        assert config.ip == sample_db_config["ip"]
        assert config.port == sample_db_config["port"]
        assert config.username == sample_db_config["username"]
        assert config.password == sample_db_config["password"]

    async def test_get_db_config(self, db_session: AsyncSession, sample_db_config: dict):
        created = await crud_db_config.create(db=db_session, obj_in=sample_db_config)
        fetched = await crud_db_config.get(db=db_session, id=created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.type == created.type

    async def test_update_db_config(self, db_session: AsyncSession, sample_db_config: dict):
        created = await crud_db_config.create(db=db_session, obj_in=sample_db_config)
        update_data = {"port": 3306, "username": "mysql_user"}
        updated = await crud_db_config.update(db=db_session, db_obj=created, obj_in=update_data)
        assert updated.port == 3306
        assert updated.username == "mysql_user"
        assert updated.type == created.type  # 未更改的字段应保持原值

    async def test_delete_db_config(self, db_session: AsyncSession, sample_db_config: dict):
        created = await crud_db_config.create(db=db_session, obj_in=sample_db_config)
        deleted = await crud_db_config.delete(db=db_session, id=created.id)
        assert deleted.id == created.id

        fetched = await crud_db_config.get(db=db_session, id=created.id)
        assert fetched is None

    async def test_get_multi_with_pagination(self, db_session: AsyncSession, sample_db_config: dict):
        for i in range(5):
            config_data = sample_db_config.copy()
            config_data["database_name"] = f"test_db_{i}"
            config_data["ip"] = f"192.168.1.{100 + i}"
            await crud_db_config.create(db=db_session, obj_in=config_data)

        items = await crud_db_config.get_multi(db=db_session, skip=0, limit=3)
        assert len(items) == 3

        items = await crud_db_config.get_multi(db=db_session, skip=3, limit=3)
        assert len(items) == 2

    async def test_filter_by_type(self, db_session: AsyncSession, sample_db_config: dict):
        await crud_db_config.create(db=db_session, obj_in=sample_db_config)

        mysql_config = sample_db_config.copy()
        mysql_config["type"] = "MYSQL"
        mysql_config["database_name"] = "mysql_db"
        mysql_config["ip"] = "192.168.1.200"
        await crud_db_config.create(db=db_session, obj_in=mysql_config)

        items = await crud_db_config.get_multi(
            db=db_session,
            filters={"type": "MYSQL"}
        )
        assert len(items) == 1
        assert items[0].type == "MYSQL"

    async def test_batch_delete(self, db_session: AsyncSession, sample_db_config: dict):
        created_ids = []
        for i in range(3):
            config_data = sample_db_config.copy()
            config_data["ip"] = f"192.168.1.{100 + i}"
            created = await crud_db_config.create(db=db_session, obj_in=config_data)
            created_ids.append(created.id)

        deleted_count = await crud_db_config.delete_multiple(db=db_session, ids=created_ids)
        assert deleted_count == 3

        for id in created_ids:
            fetched = await crud_db_config.get(db=db_session, id=id)
            assert fetched is None


class TestDbConfigService:
    async def test_create_service_validation(self, db_session: AsyncSession, sample_db_config: dict):
        """测试现在允许重复的IP:端口配置"""
        config1 = await db_config_service.create(db=db_session, obj_in=sample_db_config)
        await db_session.refresh(config1)  # 确保获取最新的状态
        id1 = config1.id
        assert id1 is not None

        # 现在应该能够创建相同IP:端口的配置
        config2 = await db_config_service.create(db=db_session, obj_in=sample_db_config)
        await db_session.refresh(config2)  # 确保获取最新的状态
        id2 = config2.id
        assert id2 is not None
        assert id2 != id1

    async def test_search_functionality(self, db_session: AsyncSession, sample_db_config: dict):
        await db_config_service.create(db=db_session, obj_in=sample_db_config)

        mysql_config = sample_db_config.copy()
        mysql_config["type"] = "MYSQL"
        mysql_config["ip"] = "10.0.0.1"
        mysql_config["username"] = "mysql_admin"
        await db_config_service.create(db=db_session, obj_in=mysql_config)

        result = await db_config_service.search(db=db_session, keyword="192.168")
        assert result["total"] == 1
        assert result["items"][0].ip == "192.168.1.100"

        result = await db_config_service.search(db=db_session, type_filter="MYSQL")
        assert result["total"] == 1
        assert result["items"][0].type == "MYSQL"

    async def test_pagination(self, db_session: AsyncSession, sample_db_config: dict):
        created_ids = []
        for i in range(10):
            config_data = sample_db_config.copy()
            config_data["ip"] = f"10.0.0.{i + 1}"
            created = await db_config_service.create(db=db_session, obj_in=config_data)
            created_ids.append(created.id)

        result = await db_config_service.get_all_with_pagination(
            db=db_session, page=1, page_size=3
        )
        assert len(result["items"]) == 3
        assert result["total"] == 10
        assert result["page"] == 1
        assert result["page_size"] == 3
        assert result["total_pages"] == 4
        assert result["has_next"] is True
        assert result["has_prev"] is False


class TestAPI:
    async def test_create_db_config_api(self, client: AsyncClient, sample_db_config: dict):
        response = await client.post("/api/v1/db-config/", json=sample_db_config)
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == sample_db_config["type"]
        assert data["database_name"] == sample_db_config["database_name"]
        assert data["ip"] == sample_db_config["ip"]
        assert "id" in data

    async def test_get_db_config_api(self, client: AsyncClient, sample_db_config: dict):
        create_response = await client.post("/api/v1/db-config/", json=sample_db_config)
        created_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/db-config/{created_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_id
        assert data["type"] == sample_db_config["type"]

        response = await client.get("/api/v1/db-config/99999")
        assert response.status_code == 404

    async def test_list_db_configs_api(self, client: AsyncClient, sample_db_config: dict):
        for i in range(3):
            config_data = sample_db_config.copy()
            config_data["database_name"] = f"test_db_{i}"
            config_data["ip"] = f"10.0.0.{i + 1}"
            await client.post("/api/v1/db-config/", json=config_data)

        response = await client.get("/api/v1/db-config/?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["has_next"] is True

    async def test_filter_db_configs_api(self, client: AsyncClient, sample_db_config: dict):
        await client.post("/api/v1/db-config/", json=sample_db_config)

        mysql_config = sample_db_config.copy()
        mysql_config["type"] = "MYSQL"
        mysql_config["ip"] = "192.168.1.200"
        await client.post("/api/v1/db-config/", json=mysql_config)

        response = await client.get("/api/v1/db-config/?type=MYSQL")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["type"] == "MYSQL"

    async def test_search_db_configs_api(self, client: AsyncClient, sample_db_config: dict):
        await client.post("/api/v1/db-config/", json=sample_db_config)

        response = await client.get("/api/v1/db-config/search?keyword=192.168")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["ip"] == "192.168.1.100"

    async def test_update_db_config_api(self, client: AsyncClient, sample_db_config: dict):
        create_response = await client.post("/api/v1/db-config/", json=sample_db_config)
        created_id = create_response.json()["id"]

        update_data = {"port": 3306, "username": "updated_user"}
        response = await client.put(f"/api/v1/db-config/{created_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["port"] == 3306
        assert data["username"] == "updated_user"

    async def test_delete_db_config_api(self, client: AsyncClient, sample_db_config: dict):
        create_response = await client.post("/api/v1/db-config/", json=sample_db_config)
        created_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/db-config/{created_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_id

        response = await client.get(f"/api/v1/db-config/{created_id}")
        assert response.status_code == 404

    async def test_batch_delete_db_configs_api(self, client: AsyncClient, sample_db_config: dict):
        created_ids = []
        for i in range(3):
            config_data = sample_db_config.copy()
            config_data["ip"] = f"10.0.0.{i + 1}"
            create_response = await client.post("/api/v1/db-config/", json=config_data)
            created_ids.append(create_response.json()["id"])

        batch_data = {"ids": created_ids}
        response = await client.delete("/api/v1/db-config/batch", json=batch_data)
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 3

        for id in created_ids:
            response = await client.get(f"/api/v1/db-config/{id}")
            assert response.status_code == 404

    async def test_create_duplicate_config_api(self, client: AsyncClient, sample_db_config: dict):
        """测试现在允许复制重复的IP:端口配置"""
        response1 = await client.post("/api/v1/db-config/", json=sample_db_config)
        assert response1.status_code == 200

        # 现在应该能够创建相同IP:端口的配置
        response2 = await client.post("/api/v1/db-config/", json=sample_db_config)
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()
        # 数据库配置API直接返回对象，不包装在data字段中
        assert data1["id"] != data2["id"]
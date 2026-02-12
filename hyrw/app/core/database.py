from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_async_engine(
    settings.SQLITE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        # 导入所有模型以确保它们被注册
        from app.models.db_config import DbConfig
        from app.models.llm_config import LlmConfig
        from app.models.nlsql_task_config import NlsqlTaskConfig
        from app.models.table_metadata import TableMetadata
        from app.models.table_metadata_extended import TableMetadataBasic, TableSampleData, TableFieldMetadata
        from app.models.table_level_prompt import TableLevelPrompt
        from app.models.table_field_prompt import TableFieldPrompt
        from app.models.table_field_relation import TableFieldRelation
        from app.models.qa_embedding import QaEmbedding
        from app.models.chat_session import ChatSession
        from app.models.conversation import Conversation
        from app.models.user_prompt_config import UserPromptConfig
        await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully!")

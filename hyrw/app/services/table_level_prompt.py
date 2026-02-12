from typing import Dict, Any, List, Optional
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.table_level_prompt import crud_table_level_prompt
from app.models.table_level_prompt import TableLevelPrompt
from app.models.nlsql_task_config import NlsqlTaskConfig
from app.models.llm_config import LlmConfig
from app.models.user_prompt_config import UserPromptConfig
from app.models.table_metadata_extended import TableMetadataBasic
from app.services.openai_service import OpenAIService

sync_engine = create_engine(
    settings.SQLITE_URL,
    connect_args={"check_same_thread": False}
)
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

logger = logging.getLogger(__name__)


class TableLevelPromptService:
    def __init__(self):
        self.crud = crud_table_level_prompt

    async def get(self, db: AsyncSession, id: int) -> TableLevelPrompt:
        obj = await self.crud.get(db, id=id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"表级别提示词ID {id} 不存在")
        return obj

    async def get_multi_with_pagination(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        table_name: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> Dict[str, Any]:
        return await self.crud.get_multi_with_pagination(
            db,
            page=page,
            page_size=page_size,
            table_name=table_name,
            task_id=task_id
        )

    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> TableLevelPrompt:
        return await self.crud.create(db, obj_in=obj_in)

    async def update(self, db: AsyncSession, *, id: int, obj_in: Dict[str, Any]) -> TableLevelPrompt:
        db_obj = await self.crud.get(db, id=id)
        if not db_obj:
            raise HTTPException(status_code=404, detail=f"表级别提示词ID {id} 不存在")
        return await self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, *, id: int) -> TableLevelPrompt:
        db_obj = await self.crud.get(db, id=id)
        if not db_obj:
            raise HTTPException(status_code=404, detail=f"表级别提示词ID {id} 不存在")
        deleted = await self.crud.delete(db, id=id)
        return deleted

    async def delete_multi(self, db: AsyncSession, *, ids: List[int]) -> Dict[str, Any]:
        if not ids:
            raise HTTPException(status_code=400, detail="删除ID列表不能为空")
        return await self.crud.delete_multi(db, ids=ids)

    async def generate_by_task_id(self, db: AsyncSession, *, task_id: int) -> Dict[str, Any]:
        sync_db = SyncSessionLocal()
        try:
            task = sync_db.query(NlsqlTaskConfig).filter(NlsqlTaskConfig.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail=f"任务ID {task_id} 不存在")

            llm_config = sync_db.query(LlmConfig).filter(LlmConfig.id == task.llm_config_id).first()
            if not llm_config:
                raise HTTPException(status_code=404, detail=f"LLM配置ID {task.llm_config_id} 不存在")

            user_prompt_config = sync_db.query(UserPromptConfig).filter(
                UserPromptConfig.id == task.user_prompt_config_id
            ).first()
            if not user_prompt_config:
                raise HTTPException(status_code=404, detail=f"用户提示词配置ID {task.user_prompt_config_id} 不存在")

            table_metadata_list = (
                sync_db.query(TableMetadataBasic)
                .options(joinedload(TableMetadataBasic.table_sample_data))
                .options(joinedload(TableMetadataBasic.table_field_metadata))
                .filter(TableMetadataBasic.table_task_id == task_id)
                .all()
            )
            if not table_metadata_list:
                raise HTTPException(status_code=404, detail="该任务暂无表元数据")

            table_notes = self._parse_json_list(user_prompt_config.table_notes)
            system_config = user_prompt_config.system_config or ""

            openai_service = OpenAIService(llm_config)
            created_ids: List[int] = []
            for table_metadata in table_metadata_list:
                prompt_data = self._build_prompt_data(table_metadata, system_config, table_notes)
                generated = self._generate_with_sample_data_fallback(
                    openai_service=openai_service,
                    prompt_data=prompt_data,
                    task_id=task_id,
                    table_name=table_metadata.table_name,
                )

                db_prompt = TableLevelPrompt(
                    task_id=task_id,
                    table_metadata_id=table_metadata.id,
                    table_name=table_metadata.table_name,
                    llm_config_id=llm_config.id,
                    table_description=generated.get("table_description", ""),
                    query_scenarios=generated.get("query_scenarios", []),
                    aggregation_scenarios=generated.get("aggregation_scenarios", []),
                    data_role=generated.get("data_role", []),
                    usage_not_scenarios=generated.get("usage_not_scenarios", []),
                    system_config=system_config,
                    table_notes=table_notes,
                    is_active=True
                )
                sync_db.add(db_prompt)
                sync_db.commit()
                sync_db.refresh(db_prompt)
                if db_prompt.id is not None:
                    created_ids.append(db_prompt.id)

            task.status = 3
            sync_db.commit()

            return {
                "generated_count": len(created_ids),
                "prompt_ids": created_ids
            }
        finally:
            sync_db.close()

    def _parse_json_list(self, value: Optional[str]) -> List[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []

    def _build_prompt_data(
        self,
        table_metadata: Any,
        system_config: str,
        table_notes: List[str]
    ) -> Dict[str, Any]:
        sample_data = table_metadata.table_sample_data[0].sample_data if table_metadata.table_sample_data else None
        field_metadata = []
        for field in table_metadata.table_field_metadata:
            field_metadata.append({
                "field_name": field.field_name,
                "field_type": field.field_type,
                "null_rate": float(field.null_rate) if field.null_rate is not None else None,
                "unique_count": field.unique_count,
                "sample_data": field.sample_data,
                "field_description": field.field_description
            })

        return {
            "table_name": table_metadata.table_name,
            "schema_name": table_metadata.schema_name,
            "system_config": system_config,
            "table_notes": table_notes,
            "table_ddl": table_metadata.table_ddl,
            "table_row_count": table_metadata.table_row_count,
            "table_description": table_metadata.table_description,
            "sample_data": sample_data,
            "field_metadata": field_metadata
        }

    def _generate_with_sample_data_fallback(
        self,
        *,
        openai_service: OpenAIService,
        prompt_data: Dict[str, Any],
        task_id: int,
        table_name: str,
    ) -> Dict[str, Any]:
        current_prompt_data = dict(prompt_data)
        current_max_tokens = self._normalize_int(getattr(openai_service.model_config, "max_tokens", None))

        retry_count = 0
        while True:
            try:
                return openai_service.generate_table_prompt(
                    current_prompt_data,
                    max_tokens_override=current_max_tokens,
                )
            except Exception as exc:
                if not self._is_context_length_error(exc):
                    raise

                retry_count += 1
                logger.warning(
                    "[table_level_prompt] context length exceeded, start fallback retry=%s task_id=%s table=%s error=%s",
                    retry_count,
                    task_id,
                    table_name,
                    str(exc),
                )

                next_max_tokens = self._reduce_completion_tokens(current_max_tokens)
                reduced_sample_data = self._reduce_sample_data_rows(current_prompt_data.get("sample_data"))
                has_max_tokens_update = next_max_tokens != current_max_tokens
                has_sample_data_update = reduced_sample_data is not None
                if not has_max_tokens_update and not has_sample_data_update:
                    raise

                if has_max_tokens_update:
                    logger.warning(
                        "[table_level_prompt] context length exceeded, reduce completion max_tokens task_id=%s table=%s max_tokens=%s->%s",
                        task_id,
                        table_name,
                        current_max_tokens,
                        next_max_tokens,
                    )
                    current_max_tokens = next_max_tokens

                if has_sample_data_update:
                    old_size = self._measure_sample_data_size(current_prompt_data.get("sample_data"))
                    new_size = self._measure_sample_data_size(reduced_sample_data)
                    logger.warning(
                        "[table_level_prompt] context length exceeded, reduce sample payload task_id=%s table=%s size=%s->%s",
                        task_id,
                        table_name,
                        old_size,
                        new_size,
                    )
                    current_prompt_data = {
                        **current_prompt_data,
                        "sample_data": reduced_sample_data,
                    }

    def _is_context_length_error(self, error: Exception) -> bool:
        error_message = str(error).lower()
        if "context_length_exceeded" in error_message:
            return True
        if "maximum context length" in error_message:
            return True
        if "too many tokens" in error_message:
            return True

        body = getattr(error, "body", None)
        if isinstance(body, dict):
            body_code = str(body.get("code", "")).lower()
            body_message = str(body.get("message", "")).lower()
            if body_code == "context_length_exceeded":
                return True
            if "maximum context length" in body_message:
                return True
            if "too many tokens" in body_message:
                return True

        response = getattr(error, "response", None)
        if response is not None:
            response_text = str(getattr(response, "text", "")).lower()
            if "maximum context length" in response_text:
                return True
            if "context_length_exceeded" in response_text:
                return True
            if "too many tokens" in response_text:
                return True

        error_type_name = type(error).__name__.lower()
        if "badrequest" in error_type_name and "maximum context length" in error_message:
            return True
        return False

    def _reduce_sample_data_rows(self, sample_data: Any) -> Optional[Any]:
        if isinstance(sample_data, list):
            row_count = len(sample_data)
            if row_count <= 1:
                return None
            reduced_row_count = max(1, row_count // 2)
            return sample_data[:reduced_row_count]

        if isinstance(sample_data, str):
            if len(sample_data) <= 200:
                return None
            return sample_data[: max(200, len(sample_data) // 2)]

        if isinstance(sample_data, dict):
            items = list(sample_data.items())
            if len(items) <= 1:
                return None
            keep_count = max(1, len(items) // 2)
            return dict(items[:keep_count])

        return None

    def _measure_sample_data_size(self, sample_data: Any) -> int:
        if isinstance(sample_data, list):
            return len(sample_data)
        if isinstance(sample_data, dict):
            return len(sample_data)
        if isinstance(sample_data, str):
            return len(sample_data)
        return 0

    def _normalize_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _reduce_completion_tokens(self, max_tokens: Optional[int]) -> Optional[int]:
        if max_tokens is None:
            return 2048
        if max_tokens > 512:
            return max(512, max_tokens // 2)
        return max_tokens

table_level_prompt_service = TableLevelPromptService()

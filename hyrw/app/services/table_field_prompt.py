from typing import Dict, Any, List, Optional
import json
import logging
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from fastapi import HTTPException

from app.core.config import settings
from app.models.nlsql_task_config import NlsqlTaskConfig
from app.models.llm_config import LlmConfig
from app.models.user_prompt_config import UserPromptConfig
from app.models.table_level_prompt import TableLevelPrompt
from app.models.table_field_prompt import TableFieldPrompt
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


class ContextLengthExhaustedError(Exception):
    pass


class TableFieldPromptService:
    def get_multi_with_pagination(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        task_id: Optional[int] = None,
        table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            query = db.query(TableFieldPrompt, TableLevelPrompt.table_name).outerjoin(
                TableLevelPrompt, TableFieldPrompt.table_level_prompt_id == TableLevelPrompt.id
            )

            if task_id is not None:
                query = query.filter(TableFieldPrompt.nlsql_task_id == task_id)
            if table_name:
                query = query.filter(TableLevelPrompt.table_name.ilike(f"%{table_name}%"))

            total = query.count()
            offset = (page - 1) * page_size
            rows = query.order_by(TableFieldPrompt.created_at.desc()).offset(offset).limit(page_size).all()

            items = []
            for field_prompt, table_name_value in rows:
                item = self._to_dict(field_prompt)
                item["table_name"] = table_name_value
                items.append(item)

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size
            }
        finally:
            db.close()

    def get(self, id: int) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            row = db.query(TableFieldPrompt, TableLevelPrompt.table_name).outerjoin(
                TableLevelPrompt, TableFieldPrompt.table_level_prompt_id == TableLevelPrompt.id
            ).filter(TableFieldPrompt.id == id).first()
            if not row:
                raise HTTPException(status_code=404, detail=f"字段提示词ID {id} 不存在")
            item = self._to_dict(row[0])
            item["table_name"] = row[1]
            return item
        finally:
            db.close()

    def create(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            db_obj = TableFieldPrompt(**obj_in)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return self._to_dict(db_obj)
        finally:
            db.close()

    def update(self, id: int, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            db_obj = db.query(TableFieldPrompt).filter(TableFieldPrompt.id == id).first()
            if not db_obj:
                raise HTTPException(status_code=404, detail=f"字段提示词ID {id} 不存在")

            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            db.commit()
            db.refresh(db_obj)
            return self._to_dict(db_obj)
        finally:
            db.close()

    def delete(self, id: int) -> None:
        db = SyncSessionLocal()
        try:
            db_obj = db.query(TableFieldPrompt).filter(TableFieldPrompt.id == id).first()
            if not db_obj:
                raise HTTPException(status_code=404, detail=f"字段提示词ID {id} 不存在")
            db.delete(db_obj)
            db.commit()
        finally:
            db.close()

    def delete_multi(self, ids: List[int]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            if not ids:
                raise HTTPException(status_code=400, detail="删除ID列表不能为空")

            objs = db.query(TableFieldPrompt).filter(TableFieldPrompt.id.in_(ids)).all()
            if not objs:
                return {"deleted_count": 0, "deleted_ids": []}

            deleted_ids = [obj.id for obj in objs]
            for obj in objs:
                db.delete(obj)
            db.commit()
            return {"deleted_count": len(deleted_ids), "deleted_ids": deleted_ids}
        finally:
            db.close()

    def generate_by_task_id(self, task_id: int) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            logger.info("[field_prompt] start generate task_id=%s", task_id)
            task = db.query(NlsqlTaskConfig).filter(NlsqlTaskConfig.id == task_id).first()
            if not task:
                logger.error("[field_prompt] task not found task_id=%s", task_id)
                raise HTTPException(status_code=404, detail=f"任务ID {task_id} 不存在")

            llm_config = db.query(LlmConfig).filter(LlmConfig.id == task.llm_config_id).first()
            if not llm_config:
                logger.error("[field_prompt] llm_config not found llm_config_id=%s", task.llm_config_id)
                raise HTTPException(status_code=404, detail=f"LLM配置ID {task.llm_config_id} 不存在")

            user_prompt_config = db.query(UserPromptConfig).filter(UserPromptConfig.id == task.user_prompt_config_id).first()
            if not user_prompt_config:
                logger.error("[field_prompt] user_prompt_config not found user_prompt_config_id=%s", task.user_prompt_config_id)
                raise HTTPException(status_code=404, detail=f"用户提示词配置ID {task.user_prompt_config_id} 不存在")

            table_metadata_list = db.query(TableMetadataBasic).options(
                joinedload(TableMetadataBasic.table_sample_data),
                joinedload(TableMetadataBasic.table_field_metadata)
            ).filter(TableMetadataBasic.table_task_id == task_id).all()
            if not table_metadata_list:
                logger.error("[field_prompt] no table metadata task_id=%s", task_id)
                raise HTTPException(status_code=404, detail="该任务暂无表元数据")


            system_config = user_prompt_config.system_config or ""
            field_notes = self._parse_json_list(user_prompt_config.field_notes)
            logger.info(
                "[field_prompt] loaded context task_id=%s tables=%s field_notes=%s model=%s",
                task_id,
                len(table_metadata_list),
                len(field_notes),
                llm_config.model_name,
            )

            openai_service = OpenAIService(llm_config)
            created_or_updated_ids: List[int] = []
            initial_batch_size = 6

            for table_metadata in table_metadata_list:
                logger.info(
                    "[field_prompt] process table task_id=%s table=%s fields=%s",
                    task_id,
                    table_metadata.table_name,
                    len(table_metadata.table_field_metadata or []),
                )
                table_prompt = db.query(TableLevelPrompt).filter(
                    TableLevelPrompt.task_id == task_id,
                    TableLevelPrompt.table_name == table_metadata.table_name
                ).first()

                table_fields = list(table_metadata.table_field_metadata or [])
                if not table_fields:
                    logger.warning(
                        "[field_prompt] skip table without fields task_id=%s table=%s",
                        task_id,
                        table_metadata.table_name,
                    )
                    continue

                current_batch_size = min(initial_batch_size, len(table_fields))
                batch_start = 0
                batch_index = 1
                while batch_start < len(table_fields):
                    batch_fields = table_fields[batch_start:batch_start + current_batch_size]
                    batch_field_names = [f.field_name for f in batch_fields]
                    logger.info(
                        "[field_prompt] openai batch start task_id=%s table=%s batch=%s batch_size=%s fields=%s",
                        task_id,
                        table_metadata.table_name,
                        batch_index,
                        len(batch_fields),
                        ",".join(batch_field_names),
                    )

                    prompt_data = self._build_fields_prompt_data(
                        table_metadata=table_metadata,
                        system_config=system_config,
                        field_notes=field_notes,
                        table_prompt=table_prompt,
                        fields=batch_fields
                    )

                    try:
                        field_results = self._generate_all_fields_with_sample_fallback(
                            openai_service=openai_service,
                            prompt_data=prompt_data,
                            task_id=task_id,
                            table_name=table_metadata.table_name,
                            batch_index=batch_index,
                        )
                        logger.info(
                            "[field_prompt] openai batch success task_id=%s table=%s batch=%s returned=%s",
                            task_id,
                            table_metadata.table_name,
                            batch_index,
                            len(field_results),
                        )
                    except ContextLengthExhaustedError as exc:
                        db.rollback()
                        if current_batch_size <= 1:
                            raise HTTPException(status_code=500, detail=f"第{batch_index}批字段生成失败: {exc}")

                        next_batch_size = max(1, current_batch_size // 2)
                        if next_batch_size == current_batch_size:
                            next_batch_size = current_batch_size - 1

                        logger.warning(
                            "[field_prompt] reduce batch size due to retryable generation failure task_id=%s table=%s batch=%s batch_size=%s->%s reason=%s",
                            task_id,
                            table_metadata.table_name,
                            batch_index,
                            current_batch_size,
                            next_batch_size,
                            str(exc),
                        )
                        current_batch_size = next_batch_size
                        continue
                    except Exception as exc:
                        db.rollback()
                        logger.exception(
                            "[field_prompt] openai batch failed task_id=%s table=%s batch=%s",
                            task_id,
                            table_metadata.table_name,
                            batch_index,
                        )
                        raise HTTPException(status_code=500, detail=f"第{batch_index}批字段生成失败: {exc}")

                    for field_result in field_results:
                        field_name = field_result.get("field_name")
                        if not field_name:
                            continue

                        field_metadata = next((f for f in batch_fields if f.field_name == field_name), None)
                        if not field_metadata:
                            continue

                        existing = db.query(TableFieldPrompt).filter(
                            TableFieldPrompt.nlsql_task_id == task_id,
                            TableFieldPrompt.table_level_prompt_id == (table_prompt.id if table_prompt else None),
                            TableFieldPrompt.field_name == field_name
                        ).first()

                        query_scenarios = self._to_json_text(field_result.get("query_scenarios", []))
                        aggregation_scenarios = self._to_json_text(field_result.get("aggregation_scenarios", []))
                        rules = self._to_json_text(field_result.get("rules", []))
                        database_usage = self._to_json_text(field_result.get("database_usage", []))

                        if existing:
                            existing.business_meaning = field_result.get("business_meaning")
                            existing.data_format = field_result.get("data_format")
                            existing.field_description = field_result.get("field_description")
                            existing.query_scenarios = query_scenarios
                            existing.aggregation_scenarios = aggregation_scenarios
                            existing.rules = rules
                            existing.database_usage = database_usage
                            existing.field_type = field_metadata.field_type
                            existing.null_rate = str(field_metadata.null_rate) if field_metadata.null_rate is not None else None
                            existing.unique_count = field_metadata.unique_count
                            existing.sample_values = field_metadata.sample_data
                            db.flush()
                            created_or_updated_ids.append(existing.id)
                        else:
                            new_obj = TableFieldPrompt(
                                nlsql_task_id=task_id,
                                table_level_prompt_id=table_prompt.id if table_prompt else None,
                                field_name=field_name,
                                business_meaning=field_result.get("business_meaning"),
                                data_format=field_result.get("data_format"),
                                field_description=field_result.get("field_description"),
                                query_scenarios=query_scenarios,
                                aggregation_scenarios=aggregation_scenarios,
                                rules=rules,
                                database_usage=database_usage,
                                field_type=field_metadata.field_type,
                                null_rate=str(field_metadata.null_rate) if field_metadata.null_rate is not None else None,
                                unique_count=field_metadata.unique_count,
                                sample_values=field_metadata.sample_data
                            )
                            db.add(new_obj)
                            db.flush()
                            created_or_updated_ids.append(new_obj.id)

                    db.commit()
                    logger.info(
                        "[field_prompt] batch committed task_id=%s table=%s batch=%s fields=%s",
                        task_id,
                        table_metadata.table_name,
                        batch_index,
                        ",".join(batch_field_names),
                    )
                    batch_start += len(batch_fields)
                    batch_index += 1

            task.status = 4
            db.commit()
            logger.info(
                "[field_prompt] finished task_id=%s generated=%s status=4",
                task_id,
                len(created_or_updated_ids),
            )

            return {
                "generated_count": len(created_or_updated_ids),
                "prompt_ids": created_or_updated_ids
            }
        except Exception:
            db.rollback()
            logger.exception("[field_prompt] generate failed task_id=%s", task_id)
            raise
        finally:
            db.close()

    def _parse_json_list(self, value: Optional[str]) -> List[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []

    def _to_json_text(self, value: Any) -> str:
        if value is None:
            return "[]"
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    def _build_fields_prompt_data(
        self,
        *,
        table_metadata: TableMetadataBasic,
        system_config: str,
        field_notes: List[str],
        table_prompt: Optional[TableLevelPrompt],
        fields: List[Any]
    ) -> Dict[str, Any]:
        all_fields = []
        for field in fields:
            all_fields.append({
                "field_name": field.field_name,
                "field_type": field.field_type,
                "null_rate": str(field.null_rate) if field.null_rate is not None else None,
                "unique_count": field.unique_count,
                "sample_data": self._normalize_field_sample_data(field.sample_data)
            })

        return {
            "table_name": table_metadata.table_name,
            "schema_name": table_metadata.schema_name,
            "system_config": system_config,
            "field_notes": field_notes,
            "table_ddl": table_metadata.table_ddl,
            "table_row_count": table_metadata.table_row_count,
            "table_description": table_metadata.table_description,
            "table_prompt": {
                "table_description": table_prompt.table_description if table_prompt else "",
                "query_scenarios": table_prompt.query_scenarios if table_prompt else [],
                "aggregation_scenarios": table_prompt.aggregation_scenarios if table_prompt else [],
                "data_role": table_prompt.data_role if table_prompt else [],
                "usage_not_scenarios": table_prompt.usage_not_scenarios if table_prompt else []
            },
            "all_fields": all_fields
        }

    def _normalize_field_sample_data(self, sample_data: Any) -> Any:
        if isinstance(sample_data, list):
            return sample_data[:2]

        if isinstance(sample_data, dict):
            items = list(sample_data.items())
            return dict(items[:5])

        if isinstance(sample_data, str):
            return sample_data[:200]

        return sample_data

    def _to_dict(self, obj: TableFieldPrompt) -> Dict[str, Any]:
        sample_values = self._normalize_sample_values(obj.sample_values)
        return {
            "id": obj.id,
            "nlsql_task_id": obj.nlsql_task_id,
            "table_level_prompt_id": obj.table_level_prompt_id,
            "field_name": obj.field_name,
            "business_meaning": obj.business_meaning,
            "data_format": obj.data_format,
            "field_description": obj.field_description,
            "query_scenarios": obj.query_scenarios,
            "aggregation_scenarios": obj.aggregation_scenarios,
            "rules": obj.rules,
            "database_usage": obj.database_usage,
            "field_type": obj.field_type,
            "null_rate": obj.null_rate,
            "unique_count": obj.unique_count,
            "sample_values": sample_values,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }

    def _generate_all_fields_with_sample_fallback(
        self,
        *,
        openai_service: OpenAIService,
        prompt_data: Dict[str, Any],
        task_id: int,
        table_name: str,
        batch_index: int,
    ) -> List[Dict[str, Any]]:
        current_prompt_data = dict(prompt_data)
        current_max_tokens = self._normalize_int(getattr(openai_service.model_config, "max_tokens", None))
        retry_count = 0
        transient_retry_count = 0
        max_transient_retries = 3

        while True:
            try:
                return openai_service.generate_all_fields_prompt(
                    current_prompt_data,
                    max_tokens_override=current_max_tokens,
                )
            except Exception as exc:
                if self._is_transient_llm_error(exc):
                    transient_retry_count += 1
                    if transient_retry_count <= max_transient_retries:
                        backoff_seconds = min(2 ** (transient_retry_count - 1), 4)
                        logger.warning(
                            "[field_prompt] transient llm error, retry same batch task_id=%s table=%s batch=%s retry=%s/%s wait=%ss error=%s",
                            task_id,
                            table_name,
                            batch_index,
                            transient_retry_count,
                            max_transient_retries,
                            backoff_seconds,
                            str(exc),
                        )
                        time.sleep(backoff_seconds)
                        continue

                    raise ContextLengthExhaustedError(f"transient llm error exceeded retry: {exc}") from exc

                transient_retry_count = 0

                if self._is_json_decode_error(exc):
                    raise ContextLengthExhaustedError(f"JSON decode failed: {exc}") from exc

                if not self._is_context_length_error(exc):
                    raise

                retry_count += 1
                logger.warning(
                    "[field_prompt] context length exceeded, fallback retry=%s task_id=%s table=%s batch=%s error=%s",
                    retry_count,
                    task_id,
                    table_name,
                    batch_index,
                    str(exc),
                )

                next_max_tokens = self._reduce_completion_tokens(current_max_tokens)
                reduced_prompt_data, reduced_fields = self._reduce_all_fields_sample_data(current_prompt_data)

                has_max_tokens_update = next_max_tokens != current_max_tokens
                has_sample_data_update = reduced_fields > 0
                if not has_max_tokens_update and not has_sample_data_update:
                    raise ContextLengthExhaustedError(str(exc)) from exc

                if has_max_tokens_update:
                    logger.warning(
                        "[field_prompt] context length exceeded, reduce completion max_tokens task_id=%s table=%s batch=%s max_tokens=%s->%s",
                        task_id,
                        table_name,
                        batch_index,
                        current_max_tokens,
                        next_max_tokens,
                    )
                    current_max_tokens = next_max_tokens

                if has_sample_data_update:
                    logger.warning(
                        "[field_prompt] context length exceeded, reduce field sample_data task_id=%s table=%s batch=%s fields_updated=%s",
                        task_id,
                        table_name,
                        batch_index,
                        reduced_fields,
                    )
                    current_prompt_data = reduced_prompt_data

    def _reduce_all_fields_sample_data(self, prompt_data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
        all_fields = prompt_data.get("all_fields")
        if not isinstance(all_fields, list):
            return prompt_data, 0

        reduced_fields = 0
        reduced_all_fields: List[Dict[str, Any]] = []
        for field in all_fields:
            if not isinstance(field, dict):
                reduced_all_fields.append(field)
                continue
            original_sample = field.get("sample_data")
            reduced_sample = self._reduce_sample_payload(original_sample)
            if reduced_sample is not None:
                reduced_fields += 1
                reduced_all_fields.append({**field, "sample_data": reduced_sample})
            else:
                reduced_all_fields.append(field)

        return {
            **prompt_data,
            "all_fields": reduced_all_fields,
        }, reduced_fields

    def _reduce_sample_payload(self, sample_data: Any) -> Optional[Any]:
        if isinstance(sample_data, list):
            if len(sample_data) <= 1:
                return None
            return sample_data[: max(1, len(sample_data) // 2)]

        if isinstance(sample_data, str):
            if len(sample_data) <= 120:
                return None
            return sample_data[: max(120, len(sample_data) // 2)]

        if isinstance(sample_data, dict):
            items = list(sample_data.items())
            if len(items) <= 1:
                return None
            return dict(items[: max(1, len(items) // 2)])

        return None

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

        return False

    def _is_transient_llm_error(self, error: Exception) -> bool:
        error_message = str(error).lower()
        if "504" in error_message:
            return True
        if "gateway timeout" in error_message:
            return True
        if "timed out" in error_message:
            return True
        if "timeout" in error_message and "http" in error_message:
            return True
        if "connection reset" in error_message:
            return True
        if "temporarily unavailable" in error_message:
            return True

        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int) and status_code in {408, 429, 500, 502, 503, 504}:
            return True

        return False

    def _is_json_decode_error(self, error: Exception) -> bool:
        if isinstance(error, json.JSONDecodeError):
            return True
        error_message = str(error).lower()
        if "jsondecodeerror" in error_message:
            return True
        if "unterminated string" in error_message:
            return True
        if "expecting value" in error_message and "char" in error_message:
            return True
        return False

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

    def _normalize_sample_values(self, value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                return [parsed]
            except json.JSONDecodeError:
                return [value]
        return [value]


table_field_prompt_service = TableFieldPromptService()

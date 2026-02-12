from typing import Dict, Any, List, Optional
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.core.config import settings
from app.models.nlsql_task_config import NlsqlTaskConfig
from app.models.llm_config import LlmConfig
from app.models.qa_embedding import QaEmbedding
from app.services.openai_service import OpenAIService


logger = logging.getLogger(__name__)

sync_engine = create_engine(
    settings.SQLITE_URL,
    connect_args={"check_same_thread": False}
)
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)


class QaEmbeddingService:
    def get_multi_with_pagination(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        task_id: Optional[int] = None,
        question: Optional[str] = None,
        is_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            query = db.query(QaEmbedding)
            if task_id is not None:
                query = query.filter(QaEmbedding.nlsql_task_id == task_id)
            if question:
                query = query.filter(QaEmbedding.question.ilike(f"%{question}%"))
            if is_enabled is not None:
                query = query.filter(QaEmbedding.is_enabled == is_enabled)

            total = query.count()
            items = query.order_by(QaEmbedding.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
            return {
                "items": [self._to_dict(item) for item in items],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        finally:
            db.close()

    def get(self, id: int) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            obj = db.query(QaEmbedding).filter(QaEmbedding.id == id).first()
            if not obj:
                raise HTTPException(status_code=404, detail=f"qa_embedding ID {id} 不存在")
            return self._to_dict(obj)
        finally:
            db.close()

    def create(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            where_conditions = obj_in.get("where_conditions")
            obj_in["where_conditions"] = self._dump_where_conditions(where_conditions)
            db_obj = QaEmbedding(**obj_in)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            logger.info("[qa_embedding] created id=%s", db_obj.id)
            return self._to_dict(db_obj)
        finally:
            db.close()

    def update(self, id: int, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            db_obj = db.query(QaEmbedding).filter(QaEmbedding.id == id).first()
            if not db_obj:
                raise HTTPException(status_code=404, detail=f"qa_embedding ID {id} 不存在")

            if "where_conditions" in obj_in:
                obj_in["where_conditions"] = self._dump_where_conditions(obj_in.get("where_conditions"))

            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            db.commit()
            db.refresh(db_obj)
            logger.info("[qa_embedding] updated id=%s", id)
            return self._to_dict(db_obj)
        finally:
            db.close()

    def delete(self, id: int) -> None:
        db = SyncSessionLocal()
        try:
            db_obj = db.query(QaEmbedding).filter(QaEmbedding.id == id).first()
            if not db_obj:
                raise HTTPException(status_code=404, detail=f"qa_embedding ID {id} 不存在")
            db.delete(db_obj)
            db.commit()
            logger.info("[qa_embedding] deleted id=%s", id)
        finally:
            db.close()

    def delete_multi(self, ids: List[int]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            if not ids:
                raise HTTPException(status_code=400, detail="删除ID列表不能为空")
            objs = db.query(QaEmbedding).filter(QaEmbedding.id.in_(ids)).all()
            if not objs:
                return {"deleted_count": 0, "deleted_ids": []}
            deleted_ids = [obj.id for obj in objs]
            for obj in objs:
                db.delete(obj)
            db.commit()
            logger.info("[qa_embedding] batch deleted count=%s", len(deleted_ids))
            return {"deleted_count": len(deleted_ids), "deleted_ids": deleted_ids}
        finally:
            db.close()

    def export_qa_pairs(self, ids: List[int]) -> List[Dict[str, Any]]:
        db = SyncSessionLocal()
        try:
            if not ids:
                raise HTTPException(status_code=400, detail="导出ID列表不能为空")
            objs = db.query(QaEmbedding).filter(QaEmbedding.id.in_(ids)).all()
            if not objs:
                return []

            qa_pairs = []
            for obj in objs:
                qa_pairs.append({
                    "question": obj.question,
                    "sql": obj.sql,
                    "where_conditions": self._load_where_conditions(obj.where_conditions),
                    "tables": self._load_tables(obj.tables),
                })

            logger.info("[qa_embedding] exported count=%s", len(qa_pairs))
            return qa_pairs
        finally:
            db.close()

    def import_qa_pairs(self, task_id: int, qa_json: List[Dict[str, Any]]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            task = db.query(NlsqlTaskConfig).filter(NlsqlTaskConfig.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail=f"任务ID {task_id} 不存在")

            logger.info("[qa_embedding] import start task_id=%s count=%s", task_id, len(qa_json))
            created_ids: List[int] = []
            for item in qa_json:
                question = item.get("question")
                sql = item.get("sql")
                if not question or not sql:
                    continue

                db_obj = QaEmbedding(
                    question=question,
                    nlsql_task_id=task_id,
                    sql=sql,
                    where_conditions=self._dump_where_conditions(item.get("where_conditions")),
                    tables=self._dump_tables(item.get("tables")),
                    is_enabled=True,
                )
                db.add(db_obj)
                db.flush()
                created_ids.append(db_obj.id)

            db.commit()
            logger.info("[qa_embedding] import finished task_id=%s created=%s", task_id, len(created_ids))
            return {
                "created_count": len(created_ids),
                "created_ids": created_ids,
            }
        except Exception:
            db.rollback()
            logger.exception("[qa_embedding] import failed task_id=%s", task_id)
            raise
        finally:
            db.close()

    def generate_where_conditions(self, qa_embedding_ids: List[int], llm_config_id: int) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            if not qa_embedding_ids:
                raise HTTPException(status_code=400, detail="qa_embedding_ids不能为空")

            llm_config = db.query(LlmConfig).filter(LlmConfig.id == llm_config_id).first()
            if not llm_config:
                raise HTTPException(status_code=404, detail=f"LLM配置ID {llm_config_id} 不存在")

            rows = db.query(QaEmbedding).filter(QaEmbedding.id.in_(qa_embedding_ids)).all()
            if not rows:
                raise HTTPException(status_code=404, detail="未找到qa_embedding记录")

            openai_service = OpenAIService(llm_config)
            success_ids: List[int] = []
            failed: List[Dict[str, Any]] = []
            logger.info("[qa_embedding] ai where generation start ids=%s", len(qa_embedding_ids))

            for row in rows:
                try:
                    where_conditions, tables = openai_service.generate_where_conditions_from_qa(
                        question=row.question,
                        sql=row.sql,
                    )
                    row.where_conditions = self._dump_where_conditions(where_conditions)
                    row.tables = self._dump_tables(tables)
                    db.flush()
                    success_ids.append(row.id)
                    logger.info("[qa_embedding] ai where generation success id=%s", row.id)
                except Exception as exc:
                    logger.exception("[qa_embedding] ai where generation failed id=%s", row.id)
                    failed.append({"id": row.id, "error": str(exc)})

            db.commit()
            logger.info("[qa_embedding] ai where generation finished success=%s failed=%s", len(success_ids), len(failed))
            return {
                "success_count": len(success_ids),
                "failed_count": len(failed),
                "updated_ids": success_ids,
                "failed_items": failed,
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _to_dict(self, obj: QaEmbedding) -> Dict[str, Any]:
        return {
            "id": obj.id,
            "question": obj.question,
            "nlsql_task_id": obj.nlsql_task_id,
            "sql": obj.sql,
            "where_conditions": self._load_where_conditions(obj.where_conditions),
            "tables": self._load_tables(obj.tables),
            "is_enabled": obj.is_enabled,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }

    def _dump_tables(self, tables: Optional[List[str]]) -> Optional[str]:
        if tables is None:
            return None
        return json.dumps(tables, ensure_ascii=False)

    def _load_tables(self, raw: Optional[str]) -> Optional[List[str]]:
        if not raw:
            return None
        if isinstance(raw, list):
            return raw
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else None
        except json.JSONDecodeError:
            return None

    def _dump_where_conditions(self, where_conditions: Optional[List[Dict[str, Any]]]) -> Optional[str]:
        if where_conditions is None:
            return None
        return json.dumps(where_conditions, ensure_ascii=False)

    def _load_where_conditions(self, raw: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        if not raw:
            return None
        if isinstance(raw, list):
            return raw
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else None
        except json.JSONDecodeError:
            return None


qa_embedding_service = QaEmbeddingService()

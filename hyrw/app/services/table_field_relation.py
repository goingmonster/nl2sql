from typing import Dict, Any, List, Optional, Tuple
import json
import logging
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker, aliased, joinedload
from fastapi import HTTPException

from app.core.config import settings
from app.models.nlsql_task_config import NlsqlTaskConfig
from app.models.llm_config import LlmConfig
from app.models.table_metadata_extended import TableMetadataBasic
from app.models.table_level_prompt import TableLevelPrompt
from app.models.table_field_prompt import TableFieldPrompt
from app.models.table_field_relation import TableFieldRelation
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


class TableFieldRelationService:
    SYSTEM_FIELD_KEYWORDS = {
        "is_delete", "deleted", "is_deleted", "delete_flag", "del_flag",
        "created_at", "updated_at", "create_time", "update_time", "timestamp",
        "gmt_create", "gmt_modified", "etl_time"
    }

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
            src_tlp = aliased(TableLevelPrompt)
            tgt_tlp = aliased(TableLevelPrompt)

            query = db.query(TableFieldRelation, src_tlp.table_name, tgt_tlp.table_name).outerjoin(
                src_tlp, TableFieldRelation.source_table_level_prompt_id == src_tlp.id
            ).outerjoin(
                tgt_tlp, TableFieldRelation.target_table_level_prompt_id == tgt_tlp.id
            )

            if task_id is not None:
                query = query.filter(TableFieldRelation.nlsql_task_id == task_id)
            if table_name:
                query = query.filter(
                    or_(
                        src_tlp.table_name.ilike(f"%{table_name}%"),
                        tgt_tlp.table_name.ilike(f"%{table_name}%")
                    )
                )

            total = query.count()
            rows = query.order_by(TableFieldRelation.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

            items = []
            for relation, src_table_name, tgt_table_name in rows:
                item = self._to_dict(relation)
                item["source_table_name"] = src_table_name
                item["target_table_name"] = tgt_table_name
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
            src_tlp = aliased(TableLevelPrompt)
            tgt_tlp = aliased(TableLevelPrompt)
            row = db.query(TableFieldRelation, src_tlp.table_name, tgt_tlp.table_name).outerjoin(
                src_tlp, TableFieldRelation.source_table_level_prompt_id == src_tlp.id
            ).outerjoin(
                tgt_tlp, TableFieldRelation.target_table_level_prompt_id == tgt_tlp.id
            ).filter(TableFieldRelation.id == id).first()

            if not row:
                raise HTTPException(status_code=404, detail=f"关系ID {id} 不存在")
            item = self._to_dict(row[0])
            item["source_table_name"] = row[1]
            item["target_table_name"] = row[2]
            return item
        finally:
            db.close()

    def create(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            db_obj = TableFieldRelation(**obj_in)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return self._to_dict(db_obj)
        finally:
            db.close()

    def update(self, id: int, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            db_obj = db.query(TableFieldRelation).filter(TableFieldRelation.id == id).first()
            if not db_obj:
                raise HTTPException(status_code=404, detail=f"关系ID {id} 不存在")

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
            db_obj = db.query(TableFieldRelation).filter(TableFieldRelation.id == id).first()
            if not db_obj:
                raise HTTPException(status_code=404, detail=f"关系ID {id} 不存在")
            db.delete(db_obj)
            db.commit()
        finally:
            db.close()

    def delete_multi(self, ids: List[int]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            if not ids:
                raise HTTPException(status_code=400, detail="删除ID列表不能为空")
            objs = db.query(TableFieldRelation).filter(TableFieldRelation.id.in_(ids)).all()
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
            logger.info("[field_relation] start generate task_id=%s", task_id)
            task = db.query(NlsqlTaskConfig).filter(NlsqlTaskConfig.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail=f"任务ID {task_id} 不存在")

            llm_config = db.query(LlmConfig).filter(LlmConfig.id == task.llm_config_id).first()
            if not llm_config:
                raise HTTPException(status_code=404, detail=f"LLM配置ID {task.llm_config_id} 不存在")

            table_prompts = db.query(TableLevelPrompt).filter(TableLevelPrompt.task_id == task_id).all()
            if len(table_prompts) < 2:
                raise HTTPException(status_code=400, detail="至少需要2个表级提示词才能生成关联关系")

            table_names = [tp.table_name for tp in table_prompts]
            metadata_list = db.query(TableMetadataBasic).options(
                joinedload(TableMetadataBasic.table_sample_data),
                joinedload(TableMetadataBasic.table_field_metadata)
            ).filter(
                TableMetadataBasic.table_task_id == task_id,
                TableMetadataBasic.table_name.in_(table_names)
            ).all()
            metadata_map = {m.table_name: m for m in metadata_list}

            field_prompts = db.query(TableFieldPrompt).filter(TableFieldPrompt.nlsql_task_id == task_id).all()
            field_prompt_by_table: Dict[int, List[TableFieldPrompt]] = {}
            for fp in field_prompts:
                tlp_id = fp.table_level_prompt_id
                if tlp_id is None:
                    continue
                field_prompt_by_table.setdefault(tlp_id, []).append(fp)

            logger.info(
                "[field_relation] context task_id=%s tables=%s field_prompts=%s",
                task_id,
                len(table_prompts),
                len(field_prompts),
            )

            openai_service = OpenAIService(llm_config)
            generated_ids: List[int] = []
            pair_count = 0

            for i in range(len(table_prompts)):
                for j in range(i + 1, len(table_prompts)):
                    source_tlp = table_prompts[i]
                    target_tlp = table_prompts[j]
                    pair_count += 1
                    logger.info(
                        "[field_relation] pair start #%s source=%s target=%s",
                        pair_count,
                        source_tlp.table_name,
                        target_tlp.table_name,
                    )

                    source_fields = self._build_field_context(
                        field_prompt_by_table.get(source_tlp.id, []),
                        metadata_map.get(source_tlp.table_name)
                    )
                    target_fields = self._build_field_context(
                        field_prompt_by_table.get(target_tlp.id, []),
                        metadata_map.get(target_tlp.table_name)
                    )
                    if not source_fields or not target_fields:
                        logger.info("[field_relation] pair skip no field context #%s", pair_count)
                        continue

                    prompt_data = {
                        "source": {
                            "table_name": source_tlp.table_name,
                            "table_description": source_tlp.table_description or "",
                            "fields": source_fields,
                        },
                        "target": {
                            "table_name": target_tlp.table_name,
                            "table_description": target_tlp.table_description or "",
                            "fields": target_fields,
                        },
                    }

                    try:
                        relations = openai_service.generate_field_relations(prompt_data)
                    except Exception as exc:
                        logger.exception("[field_relation] llm failed pair #%s", pair_count)
                        continue

                    valid = self._filter_relations(
                        relations=relations,
                        source_fields=source_fields,
                        target_fields=target_fields,
                    )
                    logger.info(
                        "[field_relation] pair result #%s raw=%s valid=%s",
                        pair_count,
                        len(relations),
                        len(valid),
                    )

                    for rel in valid:
                        source_fp = self._find_field_prompt(field_prompt_by_table.get(source_tlp.id, []), rel["source_field"])
                        target_fp = self._find_field_prompt(field_prompt_by_table.get(target_tlp.id, []), rel["target_field"])
                        if not source_fp or not target_fp:
                            continue

                        existed = db.query(TableFieldRelation).filter(
                            TableFieldRelation.nlsql_task_id == task_id,
                            TableFieldRelation.source_table_field_prompt_id == source_fp.id,
                            TableFieldRelation.target_table_field_prompt_id == target_fp.id
                        ).first()

                        if existed:
                            existed.relation_type = rel["relation_type"]
                            existed.relation_description = rel["relation_description"]
                            existed.confidence = str(rel["confidence"])
                            existed.source_table_name = source_tlp.table_name
                            existed.source_field_name = rel["source_field"]
                            existed.target_table_name = target_tlp.table_name
                            existed.target_field_name = rel["target_field"]
                            db.flush()
                            generated_ids.append(existed.id)
                        else:
                            new_obj = TableFieldRelation(
                                nlsql_task_id=task_id,
                                source_table_field_prompt_id=source_fp.id,
                                source_table_level_prompt_id=source_tlp.id,
                                source_table_name=source_tlp.table_name,
                                source_field_name=rel["source_field"],
                                target_table_field_prompt_id=target_fp.id,
                                target_table_level_prompt_id=target_tlp.id,
                                target_table_name=target_tlp.table_name,
                                target_field_name=rel["target_field"],
                                relation_type=rel["relation_type"],
                                relation_description=rel["relation_description"],
                                confidence=str(rel["confidence"]),
                            )
                            db.add(new_obj)
                            db.flush()
                            generated_ids.append(new_obj.id)

                    db.commit()
                    logger.info("[field_relation] pair committed #%s", pair_count)

            task.status = 5
            db.commit()
            logger.info("[field_relation] finished task_id=%s generated=%s", task_id, len(generated_ids))

            return {
                "generated_count": len(generated_ids),
                "relation_ids": generated_ids,
                "pairs_processed": pair_count,
            }
        except Exception:
            db.rollback()
            logger.exception("[field_relation] generate failed task_id=%s", task_id)
            raise
        finally:
            db.close()

    def _build_field_context(self, field_prompts: List[TableFieldPrompt], metadata: Optional[TableMetadataBasic]) -> List[Dict[str, Any]]:
        metadata_map: Dict[str, Any] = {}
        if metadata and metadata.table_field_metadata:
            for fm in metadata.table_field_metadata:
                metadata_map[fm.field_name] = fm

        rows: List[Dict[str, Any]] = []
        for fp in field_prompts:
            if fp.field_name is None:
                continue
            lower = fp.field_name.lower()
            if self._is_system_field(lower):
                continue

            fm = metadata_map.get(fp.field_name)
            sample_values = fp.sample_values
            if isinstance(sample_values, str):
                try:
                    sample_values = json.loads(sample_values)
                except json.JSONDecodeError:
                    pass

            rows.append({
                "field_name": fp.field_name,
                "field_type": fp.field_type or (fm.field_type if fm else None),
                "business_meaning": fp.business_meaning or "",
                "field_description": fp.field_description or (fm.field_description if fm else ""),
                "sample_values": sample_values,
            })
        return rows

    def _filter_relations(
        self,
        *,
        relations: List[Dict[str, Any]],
        source_fields: List[Dict[str, Any]],
        target_fields: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        src_names = {f["field_name"] for f in source_fields}
        tgt_names = {f["field_name"] for f in target_fields}
        seen: set[Tuple[str, str]] = set()
        cleaned: List[Dict[str, Any]] = []

        for item in relations:
            source_field = str(item.get("source_field", "")).strip()
            target_field = str(item.get("target_field", "")).strip()
            if not source_field or not target_field:
                continue
            if source_field not in src_names or target_field not in tgt_names:
                continue
            if self._is_system_field(source_field.lower()) or self._is_system_field(target_field.lower()):
                continue

            key = (source_field, target_field)
            if key in seen:
                continue
            seen.add(key)

            relation_type = str(item.get("relation_type", "business_key") or "business_key")
            relation_description = str(item.get("relation_description", item.get("description", "")) or "")
            confidence = item.get("confidence", 0.5)
            try:
                confidence_val = float(confidence)
            except Exception:
                confidence_val = 0.5
            if confidence_val < 0:
                confidence_val = 0.0
            if confidence_val > 1:
                confidence_val = 1.0

            cleaned.append({
                "source_field": source_field,
                "target_field": target_field,
                "relation_type": relation_type,
                "relation_description": relation_description,
                "confidence": confidence_val,
            })
        return cleaned

    def _is_system_field(self, name: str) -> bool:
        if name in self.SYSTEM_FIELD_KEYWORDS:
            return True
        return name.endswith("_time") or name.endswith("_at")

    def _find_field_prompt(self, field_prompts: List[TableFieldPrompt], field_name: str) -> Optional[TableFieldPrompt]:
        for fp in field_prompts:
            if fp.field_name == field_name:
                return fp
        return None

    def _to_dict(self, obj: TableFieldRelation) -> Dict[str, Any]:
        return {
            "id": obj.id,
            "nlsql_task_id": obj.nlsql_task_id,
            "source_table_field_prompt_id": obj.source_table_field_prompt_id,
            "source_table_level_prompt_id": obj.source_table_level_prompt_id,
            "source_table_name": obj.source_table_name,
            "source_field_name": obj.source_field_name,
            "target_table_field_prompt_id": obj.target_table_field_prompt_id,
            "target_table_level_prompt_id": obj.target_table_level_prompt_id,
            "target_table_name": obj.target_table_name,
            "target_field_name": obj.target_field_name,
            "relation_type": obj.relation_type,
            "relation_description": obj.relation_description,
            "confidence": obj.confidence,
            "created_at": obj.created_at,
        }


table_field_relation_service = TableFieldRelationService()

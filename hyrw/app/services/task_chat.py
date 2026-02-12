from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import logging

from fastapi import HTTPException
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.chat_session import ChatSession
from app.models.conversation import Conversation
from app.models.db_config import DbConfig
from app.models.llm_config import LlmConfig
from app.models.nlsql_task_config import NlsqlTaskConfig
from app.models.qa_embedding import QaEmbedding
from app.services.column_patch_agent import ColumnPatchAgent
from app.services.create_sql_agent import CreateSqlAgent
from app.services.query_context_agent import QueryContextAgent
from app.services.select_table_agent import SelectTableAgent
from app.services.shot_tool import ShotTool
from app.services.sql_fix_agent import SqlFixAgent


sync_engine = create_engine(
    settings.SQLITE_URL,
    connect_args={"check_same_thread": False},
)
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


logger = logging.getLogger(__name__)


class TaskChatService:
    def ask(
        self,
        *,
        task_id: int,
        question: str,
        session_id: Optional[int] = None,
        session_title: Optional[str] = None,
        description: Optional[str] = None,
        is_right: Optional[bool] = None,
    ) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            task = db.query(NlsqlTaskConfig).filter(NlsqlTaskConfig.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail=f"任务ID {task_id} 不存在")

            llm_config = db.query(LlmConfig).filter(LlmConfig.id == task.llm_config_id).first()
            if not llm_config:
                raise HTTPException(status_code=404, detail=f"LLM配置ID {task.llm_config_id} 不存在")
            if llm_config.status != 1:
                raise HTTPException(status_code=422, detail=f"LLM配置ID {llm_config.id} 未启用")

            db_config = db.query(DbConfig).filter(DbConfig.id == task.db_config_id).first()
            if not db_config:
                raise HTTPException(status_code=404, detail=f"数据库配置ID {task.db_config_id} 不存在")

            session = self._get_or_create_session(
                db=db,
                task_id=task_id,
                session_id=session_id,
                session_title=session_title,
                question=question,
            )

            qa_embeddings = (
                db.query(QaEmbedding)
                .filter(QaEmbedding.nlsql_task_id == task_id, QaEmbedding.is_enabled.is_(True))
                .all()
            )

            shot_tool = ShotTool(llm_config=llm_config, db_config=db_config)
            sql_generated, similarity = shot_tool.create_sql(question, qa_embeddings)
            sql_data = None
            select_table_result: Optional[Dict[str, Any]] = None
            selected_tables_list: List[Any] = []
            query_context: Optional[Dict[str, Any]] = None
            column_patch: Optional[Dict[str, Any]] = None
            create_sql_result: Optional[Dict[str, Any]] = None
            sql_fix_result: Optional[Dict[str, Any]] = None
            if sql_generated and similarity > 90:
                sql_data, sql_generated, sql_fix_result = self._execute_sql_with_auto_fix(
                    db=db,
                    task_id=task_id,
                    user_input=question,
                    llm_config=llm_config,
                    shot_tool=shot_tool,
                    sql=sql_generated,
                    selected_tables=[],
                )
                answer = "已匹配到高相似度问答对并执行SQL。"
            else:
                select_agent = SelectTableAgent(
                    task_id=task_id,
                    user_input=question,
                    llm_config=llm_config,
                    db=db,
                )
                select_table_result = select_agent.select_tables()
                if isinstance(select_table_result, dict):
                    selected_tables_list = select_table_result.get("selected_tables", [])
                    table_names = [
                        str(item.get("table_name"))
                        for item in selected_tables_list
                        if isinstance(item, dict) and item.get("table_name")
                    ]
                    if table_names:
                        query_agent = QueryContextAgent(
                            db=db,
                            task_id=task_id,
                            user_input=question,
                            llm_config=llm_config,
                            table_names=table_names,
                        )
                        query_context = query_agent.generate_query_context()
                        if query_context:
                            patch_agent = ColumnPatchAgent(
                                db=db,
                                task_id=task_id,
                                user_input=question,
                                llm_config=llm_config,
                                query_context=query_context,
                                table_names=table_names,
                            )
                            column_patch = patch_agent.generate_column_patch()
                            create_sql_agent = CreateSqlAgent(
                                db=db,
                                task_id=task_id,
                                user_input=question,
                                llm_config=llm_config,
                                query_context=query_context,
                                column_patches=column_patch,
                                selected_tables=table_names,
                            )
                            create_sql_result = create_sql_agent.generate_sql()
                            generated_sql_from_agent = ""
                            if isinstance(create_sql_result, dict):
                                generated_sql_from_agent = str(create_sql_result.get("sql") or "").strip()
                            if generated_sql_from_agent:
                                sql_generated = generated_sql_from_agent
                                sql_data, sql_generated, sql_fix_result = self._execute_sql_with_auto_fix(
                                    db=db,
                                    task_id=task_id,
                                    user_input=question,
                                    llm_config=llm_config,
                                    shot_tool=shot_tool,
                                    sql=sql_generated,
                                    selected_tables=table_names,
                                )
                answer = "相似度低于阈值，已触发选表代理。"

            conversation = Conversation(
                session_id=session.id,
                question=question,
                answer=answer,
                description=description,
                nlsql_task_id=task_id,
                is_right=is_right,
                sql_generated=sql_generated,
                sql_result=json.dumps(sql_data, ensure_ascii=False) if sql_data is not None else None,
                selected_tables=json.dumps(selected_tables_list, ensure_ascii=False) if selected_tables_list else None,
                query_context=json.dumps(query_context, ensure_ascii=False) if query_context is not None else None,
                column_patch=json.dumps(column_patch, ensure_ascii=False) if column_patch is not None else None,
            )
            db.add(conversation)
            db.flush()

            session.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(conversation)
            db.refresh(session)

            return {
                "session": self._session_to_dict(db, session),
                "conversation": self._conversation_to_dict(conversation, sql_data=sql_data),
                "select_table_result": select_table_result,
                "query_context": query_context,
                "column_patch": column_patch,
                "qColumnPatch": column_patch,
                "create_sql_result": create_sql_result,
                "sql_fix_result": sql_fix_result,
            }
        finally:
            db.close()

    def _execute_sql_with_auto_fix(
        self,
        *,
        db,
        task_id: int,
        user_input: str,
        llm_config: LlmConfig,
        shot_tool: ShotTool,
        sql: str,
        selected_tables: List[str],
    ) -> tuple[Any, str, Optional[Dict[str, Any]]]:
        try:
            sql_data = shot_tool.execute_sql(sql)
            return sql_data, sql, None
        except RuntimeError as exc:
            logger.warning(
                "[task_chat] sql execute failed, try auto-fix task_id=%s tables=%s error=%s",
                task_id,
                ",".join(selected_tables),
                str(exc),
            )
            fixer = SqlFixAgent(
                db=db,
                task_id=task_id,
                llm_config=llm_config,
                user_input=user_input,
                sql=sql,
                error_message=str(exc),
                selected_tables=selected_tables,
            )
            fixed_result = fixer.fix_and_execute(shot_tool=shot_tool, max_retries=3)
            if not fixed_result.get("fixed"):
                raise RuntimeError(str(fixed_result.get("error") or exc))
            fixed_sql = str(fixed_result.get("sql") or sql)
            sql_data = fixed_result.get("sql_data")
            return sql_data, fixed_sql, fixed_result

    def create_session(self, *, task_id: int, session_title: Optional[str]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            task = db.query(NlsqlTaskConfig).filter(NlsqlTaskConfig.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail=f"任务ID {task_id} 不存在")

            session = ChatSession(
                nlsql_task_id=task_id,
                session_title=session_title or f"会话-{task_id}",
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return self._session_to_dict(db, session)
        finally:
            db.close()

    def get_session(self, *, session_id: int) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail=f"会话ID {session_id} 不存在")
            return self._session_to_dict(db, session)
        finally:
            db.close()

    def update_session(self, *, session_id: int, session_title: Optional[str]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail=f"会话ID {session_id} 不存在")
            if session_title is not None:
                session.session_title = session_title
            db.commit()
            db.refresh(session)
            return self._session_to_dict(db, session)
        finally:
            db.close()

    def delete_session(self, *, session_id: int) -> None:
        db = SyncSessionLocal()
        try:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail=f"会话ID {session_id} 不存在")
            db.delete(session)
            db.commit()
        finally:
            db.close()

    def batch_delete_sessions(self, *, ids: List[int]) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            if not ids:
                raise HTTPException(status_code=400, detail="删除ID列表不能为空")
            sessions = db.query(ChatSession).filter(ChatSession.id.in_(ids)).all()
            if not sessions:
                return {"deleted_count": 0, "deleted_ids": []}
            deleted_ids = [item.id for item in sessions]
            for item in sessions:
                db.delete(item)
            db.commit()
            return {"deleted_count": len(deleted_ids), "deleted_ids": deleted_ids}
        finally:
            db.close()

    def get_sessions_with_pagination(
        self,
        *,
        page: int,
        page_size: int,
        task_id: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            query = db.query(ChatSession)
            if task_id is not None:
                query = query.filter(ChatSession.nlsql_task_id == task_id)
            if keyword:
                query = query.outerjoin(Conversation, Conversation.session_id == ChatSession.id).filter(
                    or_(
                        ChatSession.session_title.ilike(f"%{keyword}%"),
                        Conversation.question.ilike(f"%{keyword}%"),
                        Conversation.answer.ilike(f"%{keyword}%"),
                        Conversation.description.ilike(f"%{keyword}%"),
                    )
                )

            total = query.distinct(ChatSession.id).count()
            sessions = (
                query.distinct(ChatSession.id)
                .order_by(ChatSession.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            items = [self._session_to_dict(db, item) for item in sessions]
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        finally:
            db.close()

    def get_conversations_with_pagination(self, *, session_id: int, page: int, page_size: int) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail=f"会话ID {session_id} 不存在")

            query = db.query(Conversation).filter(Conversation.session_id == session_id)
            total = query.count()
            rows = (
                query.order_by(Conversation.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            items = [self._conversation_to_dict(item) for item in rows]
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        finally:
            db.close()

    def update_conversation_feedback(
        self,
        *,
        conversation_id: int,
        is_right: Optional[bool],
        description: Optional[str],
        feedback: Optional[str],
    ) -> Dict[str, Any]:
        db = SyncSessionLocal()
        try:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conversation:
                raise HTTPException(status_code=404, detail=f"对话ID {conversation_id} 不存在")

            if is_right is not None:
                conversation.is_right = is_right
            if description is not None:
                conversation.description = description
            if feedback is not None:
                conversation.feedback = feedback

            db.commit()
            db.refresh(conversation)
            return self._conversation_to_dict(conversation)
        finally:
            db.close()

    def _get_or_create_session(
        self,
        *,
        db,
        task_id: int,
        session_id: Optional[int],
        session_title: Optional[str],
        question: str,
    ) -> ChatSession:
        if session_id is not None:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail=f"会话ID {session_id} 不存在")
            if session.nlsql_task_id != task_id:
                raise HTTPException(status_code=422, detail="会话与任务ID不匹配")
            return session

        title = session_title or (question[:24] + "..." if len(question) > 24 else question)
        session = ChatSession(
            nlsql_task_id=task_id,
            session_title=title,
        )
        db.add(session)
        db.flush()
        return session

    def _session_to_dict(self, db, session: ChatSession) -> Dict[str, Any]:
        count = db.query(Conversation).filter(Conversation.session_id == session.id).count()
        return {
            "id": session.id,
            "nlsql_task_id": session.nlsql_task_id,
            "session_title": session.session_title,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "conversation_count": count,
        }

    def _conversation_to_dict(self, row: Conversation, sql_data: Optional[Any] = None) -> Dict[str, Any]:
        persisted_sql_data = None
        persisted_selected_tables = None
        persisted_query_context = None
        persisted_column_patch = None
        sql_result_raw = row.sql_result
        selected_tables_raw = row.selected_tables
        query_context_raw = row.query_context
        column_patch_raw = row.column_patch
        if sql_data is None and sql_result_raw not in (None, ""):
            try:
                persisted_sql_data = json.loads(str(sql_result_raw))
            except json.JSONDecodeError:
                persisted_sql_data = str(sql_result_raw)
        if selected_tables_raw not in (None, ""):
            try:
                persisted_selected_tables = json.loads(str(selected_tables_raw))
            except json.JSONDecodeError:
                persisted_selected_tables = str(selected_tables_raw)
        if query_context_raw not in (None, ""):
            try:
                persisted_query_context = json.loads(str(query_context_raw))
            except json.JSONDecodeError:
                persisted_query_context = str(query_context_raw)
        if column_patch_raw not in (None, ""):
            try:
                persisted_column_patch = json.loads(str(column_patch_raw))
            except json.JSONDecodeError:
                persisted_column_patch = str(column_patch_raw)

        return {
            "id": row.id,
            "session_id": row.session_id,
            "question": row.question,
            "answer": row.answer,
            "description": row.description,
            "nlsql_task_id": row.nlsql_task_id,
            "is_right": row.is_right,
            "sql_generated": row.sql_generated,
            "sql_result": str(sql_result_raw) if sql_result_raw is not None else None,
            "sql_data": sql_data if sql_data is not None else persisted_sql_data,
            "selected_tables": persisted_selected_tables,
            "query_context": persisted_query_context,
            "column_patch": persisted_column_patch,
            "feedback": row.feedback,
            "created_at": row.created_at,
        }


task_chat_service = TaskChatService()

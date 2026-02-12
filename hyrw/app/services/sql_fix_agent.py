from typing import Any, Dict, List, Optional, Tuple
import re

from sqlalchemy.orm import Session

from app.models.db_config import DbConfig
from app.models.llm_config import LlmConfig
from app.models.nlsql_task_config import NlsqlTaskConfig
from app.models.table_metadata_extended import TableMetadataBasic
from app.services.openai_service import OpenAIService
from app.services.shot_tool import ShotTool


class SqlFixAgent:
    def __init__(
        self,
        *,
        db: Session,
        task_id: int,
        llm_config: LlmConfig,
        user_input: str,
        sql: str,
        error_message: str,
        selected_tables: Optional[List[str]] = None,
    ):
        self.db = db
        self.task_id = task_id
        self.llm_config = llm_config
        self.user_input = user_input
        self.initial_sql = sql
        self.initial_error_message = error_message
        self.selected_tables = selected_tables or []
        self.openai_service = OpenAIService(llm_config)

    def fix_and_execute(
        self,
        *,
        shot_tool: ShotTool,
        max_retries: int = 3,
        timeout: int = 20,
    ) -> Dict[str, Any]:
        current_sql = self.initial_sql
        current_error = self.initial_error_message
        attempts: List[Dict[str, Any]] = []

        db_type = self._get_database_type()
        table_names = self._resolve_table_names(current_sql)
        table_ddls = self._get_table_ddls(table_names)

        for attempt in range(1, max_retries + 1):
            prompt = self._build_fix_prompt(
                db_type=db_type,
                table_ddls=table_ddls,
                failed_sql=current_sql,
                error_message=current_error,
                attempt=attempt,
                max_retries=max_retries,
            )
            fixed_sql, reason = self._call_ai_fix_sql(prompt)
            if not fixed_sql:
                attempts.append(
                    {
                        "attempt": attempt,
                        "fixed_sql": "",
                        "error": "AI未返回可执行SQL",
                        "reason": reason,
                    }
                )
                continue

            try:
                sql_data = shot_tool.execute_sql(fixed_sql, timeout=timeout)
                attempts.append(
                    {
                        "attempt": attempt,
                        "fixed_sql": fixed_sql,
                        "error": None,
                        "reason": reason,
                    }
                )
                return {
                    "fixed": True,
                    "sql": fixed_sql,
                    "sql_data": sql_data,
                    "db_type": db_type,
                    "attempts": attempts,
                }
            except RuntimeError as exc:
                current_sql = fixed_sql
                current_error = str(exc)
                attempts.append(
                    {
                        "attempt": attempt,
                        "fixed_sql": fixed_sql,
                        "error": current_error,
                        "reason": reason,
                    }
                )

        return {
            "fixed": False,
            "sql": current_sql,
            "sql_data": None,
            "db_type": db_type,
            "attempts": attempts,
            "error": current_error,
        }

    def _get_database_type(self) -> str:
        task = self.db.query(NlsqlTaskConfig).filter(NlsqlTaskConfig.id == self.task_id).first()
        if not task:
            return "unknown"
        db_config = self.db.query(DbConfig).filter(DbConfig.id == task.db_config_id).first()
        if not db_config or not db_config.type:
            return "unknown"
        return str(db_config.type)

    def _resolve_table_names(self, sql: str) -> List[str]:
        if self.selected_tables:
            return self.selected_tables

        found: List[str] = []
        pattern = re.compile(r"(?:from|join)\s+([`\"\w\.]+)", re.IGNORECASE)
        for match in pattern.finditer(sql or ""):
            raw = match.group(1).strip()
            table = raw.strip('`"')
            if "." in table:
                table = table.split(".")[-1]
            if table and table not in found:
                found.append(table)
        return found

    def _get_table_ddls(self, table_names: List[str]) -> Dict[str, str]:
        if not table_names:
            return {}
        rows = (
            self.db.query(TableMetadataBasic)
            .filter(
                TableMetadataBasic.table_task_id == self.task_id,
                TableMetadataBasic.table_name.in_(table_names),
            )
            .all()
        )
        result: Dict[str, str] = {}
        for row in rows:
            result[str(row.table_name)] = str(row.table_ddl or "")
        return result

    def _build_fix_prompt(
        self,
        *,
        db_type: str,
        table_ddls: Dict[str, str],
        failed_sql: str,
        error_message: str,
        attempt: int,
        max_retries: int,
    ) -> str:
        ddl_parts: List[str] = []
        for table_name, ddl in table_ddls.items():
            ddl_parts.append(f"表: {table_name}\nDDL:\n{ddl}\n")
        ddl_text = "\n".join(ddl_parts) if ddl_parts else "无可用DDL"

        return (
            f"你是{db_type} SQL修复专家。\n"
            f"当前是第{attempt}/{max_retries}次修复。\n\n"
            f"用户问题:\n{self.user_input}\n\n"
            f"数据库类型:\n{db_type}\n\n"
            f"本次涉及表DDL:\n{ddl_text}\n\n"
            f"失败SQL:\n{failed_sql}\n\n"
            f"执行报错:\n{error_message}\n\n"
            "要求:\n"
            "1. 只输出一个可执行SQL，不要解释，不要markdown。\n"
            "2. 必须严格符合该数据库方言。\n"
            "3. 尽量保持原查询意图不变，只修复报错相关问题。\n"
        )

    def _call_ai_fix_sql(self, prompt: str) -> Tuple[str, str]:
        response = self.openai_service.client.chat.completions.create(
            model=str(self.llm_config.model_name),
            messages=[
                {
                    "role": "system",
                    "content": "你是SQL修复专家。只返回修复后的SQL语句。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=float(getattr(self.llm_config, "temperature", 0.1) or 0.1),
            max_tokens=min(int(getattr(self.llm_config, "max_tokens", 2048) or 2048), 4096),
        )
        content = response.choices[0].message.content or ""
        sql = self._extract_sql(content)
        return sql, "ai_fix"

    def _extract_sql(self, content: str) -> str:
        text = content.strip()
        code = re.search(r"```sql\s*(.*?)\s*```", text, re.S | re.I)
        if code:
            text = code.group(1).strip()
        else:
            any_code = re.search(r"```\s*(.*?)\s*```", text, re.S)
            if any_code:
                text = any_code.group(1).strip()

        text = re.sub(r"^\s*sql\s*[:：]\s*", "", text, flags=re.I)
        while text.endswith(";"):
            text = text[:-1].rstrip()
        return text

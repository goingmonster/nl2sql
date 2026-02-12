from typing import Any, Dict, List
import json
import re

from sqlalchemy.orm import Session

from app.models.db_config import DbConfig
from app.models.llm_config import LlmConfig
from app.models.nlsql_task_config import NlsqlTaskConfig
from app.models.table_field_prompt import TableFieldPrompt
from app.models.table_level_prompt import TableLevelPrompt
from app.models.table_metadata_extended import TableMetadataBasic, TableSampleData
from app.services.generate_prompt import GeneratePrompt
from app.services.openai_service import OpenAIService


class CreateSqlAgent:
    """Generate SQL from query context and column patches."""

    def __init__(
        self,
        *,
        db: Session,
        task_id: int,
        user_input: str,
        llm_config: LlmConfig,
        query_context: Dict[str, Any],
        column_patches: Dict[str, Any],
        selected_tables: List[str],
    ):
        self.db = db
        self.task_id = task_id
        self.user_input = user_input
        self.llm_config = llm_config
        self.query_context = query_context
        self.column_patches = column_patches
        self.selected_tables = selected_tables
        self.openai_service = OpenAIService(llm_config)

    def generate_sql(self) -> Dict[str, Any]:
        database_type = self._get_database_type()
        table_metadata = self._get_table_metadata()
        table_level_info = self._get_table_level_info()
        field_level_info = self._get_field_level_info()

        prompt = self._build_sql_prompt(
            table_metadata=table_metadata,
            table_level_info=table_level_info,
            field_level_info=field_level_info,
            database_type=database_type,
        )

        result = self._call_ai_generate_sql(prompt)
        return {
            "sql": result.get("sql", ""),
            "reason": result.get("reason", ""),
            "database_type": database_type,
            "table_level_info": table_level_info,
            "field_level_info": field_level_info,
        }

    def _get_database_type(self) -> str:
        task = self.db.query(NlsqlTaskConfig).filter(NlsqlTaskConfig.id == self.task_id).first()
        if not task:
            return "unknown"
        db_config = self.db.query(DbConfig).filter(DbConfig.id == task.db_config_id).first()
        if not db_config or not db_config.type:
            return "unknown"
        return str(db_config.type)

    def _get_table_metadata(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for table_name in self.selected_tables:
            info: Dict[str, Any] = {"table_ddl": None, "sample_data": []}
            metadata = (
                self.db.query(TableMetadataBasic)
                .filter(TableMetadataBasic.table_task_id == self.task_id, TableMetadataBasic.table_name == table_name)
                .first()
            )
            if metadata:
                info["table_ddl"] = metadata.table_ddl
                samples = (
                    self.db.query(TableSampleData)
                    .filter(TableSampleData.table_metadata_id == metadata.id)
                    .limit(2)
                    .all()
                )
                sample_data: List[Any] = []
                for sample in samples:
                    value = sample.sample_data
                    if isinstance(value, str):
                        try:
                            parsed = json.loads(value)
                            if isinstance(parsed, list):
                                sample_data.extend(parsed[:2])
                            else:
                                sample_data.append(parsed)
                        except json.JSONDecodeError:
                            sample_data.append(value)
                    else:
                        sample_data.append(value)
                info["sample_data"] = sample_data
            result[table_name] = info
        return result

    def _get_table_level_info(self) -> Dict[str, Any]:
        rows = (
            self.db.query(TableLevelPrompt)
            .filter(
                TableLevelPrompt.task_id == self.task_id,
                TableLevelPrompt.table_name.in_(self.selected_tables),
                TableLevelPrompt.is_active.is_(True),
            )
            .all()
        )
        data: Dict[str, Any] = {}
        for row in rows:
            data[row.table_name] = {
                "table_description": row.table_description,
                "query_scenarios": row.query_scenarios,
                "aggregation_scenarios": row.aggregation_scenarios,
                "data_role": row.data_role,
                "usage_not_scenarios": row.usage_not_scenarios,
            }
        return data

    def _get_field_level_info(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        table_usage = self.query_context.get("table_usage", {}) if isinstance(self.query_context, dict) else {}
        prompts = (
            self.db.query(TableLevelPrompt)
            .filter(
                TableLevelPrompt.task_id == self.task_id,
                TableLevelPrompt.table_name.in_(self.selected_tables),
                TableLevelPrompt.is_active.is_(True),
            )
            .all()
        )
        table_prompt_map = {p.table_name: p for p in prompts}

        for table_name in self.selected_tables:
            table_fields: Dict[str, Any] = {}
            prompt = table_prompt_map.get(table_name)
            if not prompt:
                data[table_name] = table_fields
                continue

            query = self.db.query(TableFieldPrompt).filter(
                TableFieldPrompt.nlsql_task_id == self.task_id,
                TableFieldPrompt.table_level_prompt_id == prompt.id,
            )

            usage = table_usage.get(table_name, {}) if isinstance(table_usage, dict) else {}
            filter_fields = usage.get("filter_fields", []) if isinstance(usage, dict) else []
            if isinstance(filter_fields, list) and filter_fields:
                query = query.filter(TableFieldPrompt.field_name.in_(filter_fields))

            fields = query.all()
            for field in fields:
                table_fields[field.field_name] = {
                    "business_meaning": field.business_meaning,
                    "data_format": field.data_format,
                    "field_description": field.field_description,
                    "field_type": field.field_type,
                    "null_rate": field.null_rate,
                    "unique_count": field.unique_count,
                    "sample_data": field.sample_values,
                }
            data[table_name] = table_fields

        return data

    def _build_sql_prompt(
        self,
        *,
        table_metadata: Dict[str, Any],
        table_level_info: Dict[str, Any],
        field_level_info: Dict[str, Any],
        database_type: str,
    ) -> str:
        generator = GeneratePrompt(self.db)
        extras: List[str] = [f"数据库类型: {database_type}"]
        if self.query_context:
            extras.append(f"查询上下文: {json.dumps(self.query_context, ensure_ascii=False)}")
        if self.column_patches:
            extras.append(f"列补丁: {json.dumps(self.column_patches, ensure_ascii=False)}")

        return generator.build_complete_sql_prompt(
            user_input=self.user_input,
            table_names=self.selected_tables,
            other_messages="\n".join(extras),
            database_type=database_type,
            task_id=self.task_id,
            table_metadata=table_metadata,
            table_level_info=table_level_info,
            field_level_info=field_level_info,
            query_context=self.query_context,
        )

    def _call_ai_generate_sql(self, prompt: str) -> Dict[str, Any]:
        response = self.openai_service.client.chat.completions.create(
            model=str(self.llm_config.model_name),
            messages=[
                {
                    "role": "system",
                    "content": "你是SQL生成专家。请按格式返回【SQL】和【理由】。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=float(getattr(self.llm_config, "temperature", 0.2) or 0.2),
            max_tokens=min(int(getattr(self.llm_config, "max_tokens", 2048) or 2048), 4096),
        )
        return self._parse_sql_response(response.choices[0].message.content or "")

    def _parse_sql_response(self, content: str) -> Dict[str, Any]:
        text = content.strip()
        sql_match = re.search(r"【SQL】\s*(.*?)\s*(【理由】|$)", text, re.S)
        reason_match = re.search(r"【理由】\s*(.*)$", text, re.S)

        sql = sql_match.group(1).strip() if sql_match else ""
        reason = reason_match.group(1).strip() if reason_match else ""

        if not sql:
            code = re.search(r"```sql\s*(.*?)\s*```", text, re.S | re.I)
            if code:
                sql = code.group(1).strip()

        return {"sql": sql, "reason": reason}

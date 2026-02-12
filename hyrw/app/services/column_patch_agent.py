from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.llm_config import LlmConfig
from app.services.generate_prompt import GeneratePrompt
from app.services.openai_service import OpenAIService


class ColumnPatchAgent:
    def __init__(
        self,
        *,
        db: Session,
        task_id: int,
        user_input: str,
        llm_config: LlmConfig,
        query_context: Dict[str, Any],
        table_names: List[str],
    ):
        self.db = db
        self.task_id = task_id
        self.user_input = user_input
        self.llm_config = llm_config
        self.query_context = query_context
        self.table_names = table_names
        self.openai_service = OpenAIService(llm_config)

    def generate_column_patch(self) -> Dict[str, Any]:
        filtered_tables = self._filter_tables_by_fields()
        if not filtered_tables:
            return {
                "column_patches": {},
                "reason": "没有找到需要过滤的表或字段",
            }

        prompt = self._build_column_patch_prompt(filtered_tables)
        response = self.openai_service.client.chat.completions.create(
            model=str(self.llm_config.model_name),
            messages=[
                {"role": "system", "content": "你是SQL WHERE条件生成专家。仅输出每表WHERE和原因。"},
                {"role": "user", "content": prompt},
            ],
            temperature=float(getattr(self.llm_config, "temperature", 0.2) or 0.2),
            max_tokens=min(int(getattr(self.llm_config, "max_tokens", 2048) or 2048), 4096),
        )

        content = response.choices[0].message.content or ""
        patches = self._parse_response(content)
        return {
            "column_patches": patches,
            "tables": list(filtered_tables.keys()),
        }

    def _filter_tables_by_fields(self) -> Dict[str, List[str]]:
        filtered: Dict[str, List[str]] = {}
        table_usage = self.query_context.get("table_usage", {}) if isinstance(self.query_context, dict) else {}

        for table_name in self.table_names:
            usage = table_usage.get(table_name, {}) if isinstance(table_usage, dict) else {}
            fields = usage.get("filter_fields", []) if isinstance(usage, dict) else []
            if isinstance(fields, list) and fields:
                filtered[table_name] = [str(item) for item in fields if item]

        return filtered

    def _build_column_patch_prompt(self, filtered_tables: Dict[str, List[str]]) -> str:
        generator = GeneratePrompt(self.db)
        return generator.build_column_patch_prompt(
            user_input=self.user_input,
            query_context=self.query_context,
            table_names=list(filtered_tables.keys()),
            task_id=self.task_id,
        )

    def _parse_response(self, content: str) -> Dict[str, Any]:
        patches: Dict[str, Any] = {}
        current_table = None
        current_where = None
        current_reason = None

        for raw in content.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("[TABLE]"):
                if current_table:
                    patches[current_table] = {
                        "where": current_where or "WHERE 1=1",
                        "reason": current_reason or "无规则",
                    }
                current_table = line.replace("[TABLE]", "", 1).strip()
                current_where = None
                current_reason = None
                continue

            if line.startswith("WHERE"):
                current_where = line
                continue

            if line.startswith("REASON:"):
                current_reason = line.replace("REASON:", "", 1).strip()

        if current_table:
            patches[current_table] = {
                "where": current_where or "WHERE 1=1",
                "reason": current_reason or "无规则",
            }
        return patches

from collections import defaultdict
from typing import List, Dict, Any
import re

from sqlalchemy.orm import Session

from app.models.llm_config import LlmConfig
from app.services.generate_prompt import GeneratePrompt
from app.services.openai_service import OpenAIService


class QueryContextAgent:
    def __init__(
        self,
        *,
        db: Session,
        task_id: int,
        user_input: str,
        llm_config: LlmConfig,
        table_names: List[str],
    ):
        self.db = db
        self.task_id = task_id
        self.user_input = user_input
        self.llm_config = llm_config
        self.table_names = table_names
        self.openai_service = OpenAIService(llm_config)

    def generate_query_context(self) -> Dict[str, Any]:
        prompt = self._build_query_context_prompt()
        print(prompt)
        response = self.openai_service.client.chat.completions.create(
            model=str(self.llm_config.model_name),
            messages=[
                {"role": "system", "content": "你是一个查询上下文分析器，严格按行协议返回。"},
                {"role": "user", "content": prompt},
            ],
            temperature=float(getattr(self.llm_config, "temperature", 0.2) or 0.2),
            max_tokens=min(int(getattr(self.llm_config, "max_tokens", 4096) or 4096), 4096),
        )

        content = response.choices[0].message.content or ""
        return self._parse_response(content)

    def _build_query_context_prompt(self) -> str:
        generator = GeneratePrompt(self.db)
        return generator.build_query_context_prompt(
            user_input=self.user_input,
            table_names=self.table_names,
            task_id=self.task_id,
        )

    def _parse_response(self, content: str) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {
            "allowed_tables": [],
            "driver_table": None,
            "joins": [],
            "table_usage": defaultdict(dict),
        }

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if key == "ALLOWED_TABLES":
                ctx["allowed_tables"] = [v.strip() for v in value.split(",") if v.strip()]
            elif key == "DRIVER_TABLE":
                ctx["driver_table"] = value
            elif key == "JOIN":
                if "->" in value:
                    left, right = value.split("->", 1)
                    ctx["joins"].append({"from": left.strip(), "to": right.strip()})
            elif key.startswith("TABLE_USAGE."):
                m = re.match(r"TABLE_USAGE\.([^.]+)\.([A-Z_]+)", key)
                if not m:
                    continue
                table, usage_type = m.groups()
                if usage_type == "WHERE_FIELDS":
                    ctx["table_usage"][table]["filter_fields"] = [v.strip() for v in value.split(",") if v.strip()]
                elif usage_type == "GROUP_BY_FIELDS":
                    ctx["table_usage"][table]["group_by_fields"] = [v.strip() for v in value.split(",") if v.strip()]
                elif usage_type == "AGG_FIELDS":
                    ctx["table_usage"][table]["agg_fields"] = [v.strip() for v in value.split(",") if v.strip()]
                elif usage_type == "JOIN_KEY":
                    ctx["table_usage"][table]["join_key"] = value

        ctx["table_usage"] = dict(ctx["table_usage"])
        return ctx

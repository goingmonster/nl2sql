from typing import Any, Dict, List
import json

from openai import OpenAI
from sqlalchemy.orm import Session

from app.models.llm_config import LlmConfig
from app.models.table_level_prompt import TableLevelPrompt
from app.models.table_metadata_extended import TableMetadataBasic


class SelectTableAgent:
    def __init__(self, *, task_id: int, user_input: str, llm_config: LlmConfig, db: Session):
        self.task_id = task_id
        self.user_input = user_input
        self.llm_config = llm_config
        self.db = db
        base_url = getattr(llm_config, "base_url", None)
        api_key = getattr(llm_config, "api_key", None)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url != "https://api.openai.com/v1" else None,
        )

    def select_tables(self) -> Dict[str, Any]:
        table_rows = self._load_table_contexts()
        if not table_rows:
            return {
                "selected_tables": [],
                "reason": "当前任务没有可用的表元数据或表级提示词",
            }

        prompt = self._build_prompt(table_rows)
        print(prompt)
        content = self._chat(prompt)
        parsed = self._parse_json(content)

        selected = parsed.get("selected_tables", []) if isinstance(parsed, dict) else []
        reason = parsed.get("reason", "") if isinstance(parsed, dict) else ""

        if not isinstance(selected, list):
            selected = []

        table_name_to_id = {item["table_name"]: item["table_id"] for item in table_rows}
        selected_items: List[Dict[str, Any]] = []
        for item in selected:
            if not isinstance(item, str):
                continue
            table_name = item.strip()
            if table_name in table_name_to_id:
                selected_items.append({
                    "table_name": table_name,
                    "table_id": table_name_to_id[table_name],
                })

        return {
            "selected_tables": selected_items,
            "reason": reason,
            "candidate_count": len(table_rows),
        }

    def _load_table_contexts(self) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(TableLevelPrompt, TableMetadataBasic)
            .join(TableMetadataBasic, TableLevelPrompt.table_metadata_id == TableMetadataBasic.id)
            .filter(TableLevelPrompt.task_id == self.task_id, TableLevelPrompt.is_active.is_(True))
            .all()
        )

        contexts: List[Dict[str, Any]] = []
        for prompt, metadata in rows:
            contexts.append(
                {
                    "table_id": metadata.id,
                    "table_name": prompt.table_name,
                    "table_description": prompt.table_description or metadata.table_description or "",
                    "query_scenarios": prompt.query_scenarios or [],
                    "aggregation_scenarios": prompt.aggregation_scenarios or [],
                    "data_role": prompt.data_role or [],
                    "usage_not_scenarios": prompt.usage_not_scenarios or [],
                }
            )
        return contexts

    def _build_prompt(self, table_rows: List[Dict[str, Any]]) -> str:
        lines: List[str] = []
        lines.append("你是一个选表助手，需要根据用户问题从候选表中选择最相关的1-3张表。")
        lines.append("仅返回JSON，不要markdown。")
        lines.append("\n用户问题:")
        lines.append(self.user_input)
        lines.append("\n候选表:")

        for index, item in enumerate(table_rows, start=1):
            lines.append(f"{index}. table_name={item['table_name']}")
            lines.append(f"   table_id={item['table_id']}")
            lines.append(f"   table_description={item['table_description']}")
            lines.append(f"   query_scenarios={json.dumps(item['query_scenarios'], ensure_ascii=False)}")
            lines.append(f"   aggregation_scenarios={json.dumps(item['aggregation_scenarios'], ensure_ascii=False)}")
            lines.append(f"   data_role={json.dumps(item['data_role'], ensure_ascii=False)}")
            lines.append(f"   usage_not_scenarios={json.dumps(item['usage_not_scenarios'], ensure_ascii=False)}")

        lines.append(
            "\n输出格式:\n"
            "{\n"
            '  "selected_tables": ["table_a", "table_b"],\n'
            '  "reason": "简要说明原因"\n'
            "}"
        )
        return "\n".join(lines)

    def _chat(self, prompt: str) -> str:
        temperature_value = getattr(self.llm_config, "temperature", None)
        temperature = float(temperature_value) if temperature_value is not None else 0.2
        model_name = getattr(self.llm_config, "model_name", None)
        if model_name is None:
            raise ValueError("模型名称不能为空")
        max_tokens = getattr(self.llm_config, "max_tokens", None)

        response = self.client.chat.completions.create(
            model=str(model_name),
            messages=[
                {"role": "system", "content": "你是一个严谨的数据分析选表助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or "{}"

    def _parse_json(self, content: str) -> Dict[str, Any]:
        text = content.strip()
        if text.startswith("```json"):
            first_newline = text.find("\n")
            last_triple = text.rfind("```")
            if first_newline != -1 and last_triple != -1:
                text = text[first_newline + 1:last_triple].strip()
        elif text.startswith("```"):
            first_newline = text.find("\n")
            last_triple = text.rfind("```")
            if first_newline != -1 and last_triple != -1:
                text = text[first_newline + 1:last_triple].strip()

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            left = text.find("{")
            right = text.rfind("}")
            if left != -1 and right != -1 and right > left:
                try:
                    parsed = json.loads(text[left:right + 1])
                    return parsed if isinstance(parsed, dict) else {}
                except json.JSONDecodeError:
                    return {}
            return {}

from typing import Dict, Any, List, Tuple
import json
from openai import OpenAI, BadRequestError
from app.models.llm_config import LlmConfig


class OpenAIService:
    def __init__(self, model_config: LlmConfig):
        self.model_config = model_config
        base_url = getattr(model_config, "base_url", None)
        api_key = getattr(model_config, "api_key", None)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url != "https://api.openai.com/v1" else None
        )

    def _is_context_window_error(self, exc: BadRequestError) -> bool:
        message = str(exc).lower()
        return (
            "contextwindowexceedederror" in message
            or "maximum context length" in message
            or ("max_tokens" in message and "too large" in message)
        )

    def _reduce_max_tokens_by_one_third(self, current_max_tokens: int) -> int:
        next_max_tokens = current_max_tokens - current_max_tokens // 3
        if next_max_tokens >= current_max_tokens:
            next_max_tokens = current_max_tokens - 1
        return max(1, next_max_tokens)

    def generate_table_prompt(
        self,
        prompt_data: Dict[str, Any],
        *,
        max_tokens_override: int | None = None,
    ) -> Dict[str, Any]:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(prompt_data)

        temperature_value = getattr(self.model_config, "temperature", None)
        temperature = float(temperature_value) if temperature_value is not None else 0.7

        model_name = getattr(self.model_config, "model_name", None)
        if model_name is None:
            raise ValueError("模型名称不能为空")
        max_tokens = max_tokens_override if max_tokens_override is not None else getattr(self.model_config, "max_tokens", None)

        response = self.client.chat.completions.create(
            model=str(model_name),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content or ""
        return self._parse_json_content(content)

    def generate_chat_response(self, messages: List[Dict[str, str]]) -> str:
        temperature_value = getattr(self.model_config, "temperature", None)
        temperature = float(temperature_value) if temperature_value is not None else 0.7

        model_name = getattr(self.model_config, "model_name", None)
        if model_name is None:
            raise ValueError("模型名称不能为空")
        max_tokens = getattr(self.model_config, "max_tokens", None)

        response = self.client.chat.completions.create(
            model=str(model_name),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def _parse_json_content(self, content: str) -> Dict[str, Any]:
        content = content.strip()
        if content.startswith("```json"):
            first_newline = content.find("\n")
            last_triple = content.rfind("```")
            if first_newline != -1 and last_triple != -1:
                content = content[first_newline + 1:last_triple].strip()
        elif content.startswith("```"):
            first_newline = content.find("\n")
            last_triple = content.rfind("```")
            if first_newline != -1 and last_triple != -1:
                content = content[first_newline + 1:last_triple].strip()

        return json.loads(content)

    def _parse_json_flexible(self, content: str) -> Any:
        content = content.strip()
        if content.startswith("```json"):
            first_newline = content.find("\n")
            last_triple = content.rfind("```")
            if first_newline != -1 and last_triple != -1:
                content = content[first_newline + 1:last_triple].strip()
        elif content.startswith("```"):
            first_newline = content.find("\n")
            last_triple = content.rfind("```")
            if first_newline != -1 and last_triple != -1:
                content = content[first_newline + 1:last_triple].strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1 and end > start:
                return json.loads(content[start:end + 1])
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(content[start:end + 1])
            raise

    def _build_system_prompt(self) -> str:
        return (
            "你是一个专业的数据分析专家，擅长为数据表生成精确的提示词描述。\n\n"
            "请根据提供的表结构信息，生成一个严格符合JSON格式的响应。"
            "响应必须是一个有效的JSON对象，不要包含任何markdown代码块标记（如```json或```）。\n\n"
            "JSON格式如下：\n"
            "{\n"
            "  \"table_description\": \"表的详细描述\",\n"
            "  \"query_scenarios\": [\"查询场景1\", \"查询场景2\", ...],\n"
            "  \"aggregation_scenarios\": [\"聚合场景1\", \"聚合场景2\", ...],\n"
            "  \"data_role\": [\"角色1\", \"角色2\", ...],\n"
            "  \"usage_not_scenarios\": [\"不适合场景1\", \"不适合场景2\", ...]\n"
            "}\n\n"
            "注意事项：\n"
            "1. table_description：用简洁明确的语言描述表的用途和内容\n"
            "2. query_scenarios：列出3-5个常见的查询场景\n"
            "3. aggregation_scenarios：列出2-4个聚合分析场景\n"
            "4. data_role：列出此表在数据库中扮演的角色\n"
            "5. usage_not_scenarios：列出不适合使用此表的场景\n"
            "6. 直接返回JSON对象，不要使用任何markdown格式"
        )

    def _build_user_prompt(self, data: Dict[str, Any]) -> str:
        table_notes_text = "\n".join(data["table_notes"]) if data["table_notes"] else "无"
        prompt = (
            "请为以下表生成提示词描述：\n\n"
            f"表名：{data['table_name']}\n"
            f"模式：{data['schema_name']}\n\n"
            "系统级别描述：\n"
            f"{data['system_config']}\n\n"
            "表注意事项：\n"
            f"{table_notes_text}\n\n"
            "表DDL：\n"
            f"{data['table_ddl']}\n\n"
            f"表行数：{data.get('table_row_count', '未知')}\n"
            f"表描述：{data.get('table_description', '无')}\n\n"
            "字段信息：\n"
        )

        for field in data["field_metadata"]:
            field_sample_data = json.dumps(field.get("sample_data"), ensure_ascii=False) if field.get("sample_data") is not None else "无"
            if len(field_sample_data) > 100:
                field_sample_data = field_sample_data[:100]
            prompt += (
                f"- {field['field_name']} ({field['field_type']})\n"
                f"  空值率：{field.get('null_rate', '未知')}\n"
                f"  唯一值数：{field.get('unique_count', '未知')}\n"
                f"  样例数据：{field_sample_data}\n"
            )

        sample_data_text = self._format_table_sample_data_for_prompt(data.get("sample_data"))
        prompt += f"\n样例数据：\n{sample_data_text}\n\n"
        prompt += "请基于以上信息生成JSON格式的提示词响应。"
        return prompt

    def _format_table_sample_data_for_prompt(self, sample_data: Any) -> str:
        if sample_data is None:
            return "无"

        compact_sample = self._compact_sample_payload(sample_data)
        text = json.dumps(compact_sample, ensure_ascii=False)
        if len(text) > 2000:
            return text[:2000]
        return text

    def _compact_sample_payload(self, sample_data: Any) -> Any:
        if isinstance(sample_data, list):
            return sample_data[:3]
        if isinstance(sample_data, dict):
            compact_dict: Dict[str, Any] = {}
            for key, value in sample_data.items():
                if isinstance(value, str) and len(value) > 200:
                    compact_dict[str(key)] = value[:200]
                else:
                    compact_dict[str(key)] = value
            return compact_dict
        if isinstance(sample_data, str):
            if len(sample_data) > 2000:
                return sample_data[:2000]
            return sample_data
        return sample_data

    def generate_all_fields_prompt(
        self,
        prompt_data: Dict[str, Any],
        *,
        max_tokens_override: int | None = None,
    ) -> List[Dict[str, Any]]:
        system_prompt = self._build_all_fields_system_prompt()
        user_prompt = self._build_all_fields_user_prompt(prompt_data)

        temperature_value = getattr(self.model_config, "temperature", None)
        temperature = float(temperature_value) if temperature_value is not None else 0.7
        model_name = getattr(self.model_config, "model_name", None)
        if model_name is None:
            raise ValueError("模型名称不能为空")
        max_tokens = max_tokens_override if max_tokens_override is not None else getattr(self.model_config, "max_tokens", None)

        response = self.client.chat.completions.create(
            model=str(model_name),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content or ""
        print("ai 返回未json序列化的字段提示词")
        print(content)
        parsed = self._parse_json_content(content)
        if isinstance(parsed, dict) and isinstance(parsed.get("fields"), list):
            return parsed["fields"]
        if isinstance(parsed, list):
            return parsed
        raise ValueError("字段提示词返回格式错误")

    def generate_field_relations(self, prompt_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        system_prompt = self._build_field_relations_system_prompt()
        user_prompt = self._build_field_relations_user_prompt(prompt_data)

        temperature_value = getattr(self.model_config, "temperature", None)
        temperature = float(temperature_value) if temperature_value is not None else 0.4
        model_name = getattr(self.model_config, "model_name", None)
        if model_name is None:
            raise ValueError("模型名称不能为空")
        max_tokens = getattr(self.model_config, "max_tokens", None)

        current_max_tokens = int(max_tokens) if max_tokens is not None else None
        retry_times = 0
        while True:
            try:
                response = self.client.chat.completions.create(
                    model=str(model_name),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=current_max_tokens
                )
                break
            except BadRequestError as exc:
                if current_max_tokens is None or not self._is_context_window_error(exc):
                    raise
                if current_max_tokens <= 1 or retry_times >= 12:
                    raise
                current_max_tokens = self._reduce_max_tokens_by_one_third(current_max_tokens)
                retry_times += 1

        content = response.choices[0].message.content or "[]"
        parsed = self._parse_json_flexible(content)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and isinstance(parsed.get("relations"), list):
            return parsed["relations"]
        return []

    def generate_where_conditions_from_qa(self, question: str, sql: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        system_prompt = (
            "你是SQL条件提取专家。请完成两个任务："
            "1. 从SQL中提取WHERE条件"
            "2. 识别SQL中使用的所有表名（FROM、JOIN子句中的表）"
            "不要返回markdown，不要返回额外文本。"
            "输出必须是严格的JSON格式："
            "{\"where_conditions\": [...], \"tables\": [\"表1\", \"表2\"]}"
            "where_conditions每个元素格式：{\"field\":\"\",\"operator\":\"eq|ne|gt|lt|gte|lte|like|in\",\"value\":任意类型,\"description\":\"\"}"
            "如果没有条件，where_conditions返回空数组[]。"
            "tables返回所有用到的表名，如果没有表返回空数组[]。"
        )
        user_prompt = (
            f"问题:\n{question}\n\n"
            f"SQL:\n{sql}\n\n"
            "请提取WHERE条件和表名，严格返回JSON对象。"
        )

        temperature_value = getattr(self.model_config, "temperature", None)
        temperature = float(temperature_value) if temperature_value is not None else 0.2
        model_name = getattr(self.model_config, "model_name", None)
        if model_name is None:
            raise ValueError("模型名称不能为空")
        max_tokens = getattr(self.model_config, "max_tokens", None)

        response = self.client.chat.completions.create(
            model=str(model_name),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content or "{}"
        parsed = self._parse_json_flexible(content)
        if not isinstance(parsed, dict):
            return [], []

        where_conditions_raw = parsed.get("where_conditions", [])
        if not isinstance(where_conditions_raw, list):
            where_conditions_raw = []

        cleaned_where: List[Dict[str, Any]] = []
        for item in where_conditions_raw:
            if not isinstance(item, dict):
                continue
            field = item.get("field")
            operator = item.get("operator")
            if not field or not operator:
                continue
            cleaned_where.append(
                {
                    "field": str(field),
                    "operator": str(operator),
                    "value": item.get("value"),
                    "description": str(item.get("description", "")),
                }
            )

        tables_raw = parsed.get("tables", [])
        if isinstance(tables_raw, list):
            tables = [str(t) for t in tables_raw if t]
        else:
            tables = []

        return cleaned_where, tables

    def _build_all_fields_system_prompt(self) -> str:
        return (
            "你是一个专业的数据分析专家，擅长为数据表的所有字段生成精确的提示词描述。\n\n"
            "请根据提供的表信息和所有字段信息，生成一个严格符合JSON格式的响应。"
            "响应必须是一个有效的JSON对象，不要包含任何markdown代码块标记（如```json或```）。\n\n"
            "JSON格式如下：\n"
            "{\n"
            "  \"fields\": [\n"
            "    {\n"
            "      \"field_name\": \"字段名称\",\n"
            "      \"business_meaning\": \"字段的业务含义\",\n"
            "      \"data_format\": \"数据格式说明\",\n"
            "      \"field_description\": \"字段的详细描述\",\n"
            "      \"query_scenarios\": [\"查询场景1\", \"查询场景2\"],\n"
            "      \"aggregation_scenarios\": [\"聚合场景1\", \"聚合场景2\"],\n"
            "      \"rules\": [\"规则1\", \"规则2\"],\n"
            "      \"database_usage\": [\"数据库用法1\", \"数据库用法2\"]\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "直接返回JSON对象，不要使用markdown格式。"
        )

    def _build_all_fields_user_prompt(self, data: Dict[str, Any]) -> str:
        field_notes_text = "\n".join(data.get("field_notes", [])) if data.get("field_notes") else "无"
        table_prompt = data.get("table_prompt") or {}
        prompt = (
            "请为以下表的字段生成提示词：\n\n"
            f"表名：{data.get('table_name')}\n"
            f"模式：{data.get('schema_name')}\n\n"
            "系统级描述：\n"
            f"{data.get('system_config', '')}\n\n"
            "字段注意事项：\n"
            f"{field_notes_text}\n\n"
            "表DDL：\n"
            f"{data.get('table_ddl', '')}\n\n"
            f"表描述：{data.get('table_description', '')}\n"
            f"表行数：{data.get('table_row_count', '未知')}\n\n"
            "表级提示词：\n"
            f"表描述：{table_prompt.get('table_description', '')}\n"
            f"查询场景：{table_prompt.get('query_scenarios', [])}\n"
            f"聚合场景：{table_prompt.get('aggregation_scenarios', [])}\n"
            f"数据角色：{table_prompt.get('data_role', [])}\n"
            f"不推荐场景：{table_prompt.get('usage_not_scenarios', [])}\n\n"
            "字段信息：\n"
        )

        all_fields = data.get("all_fields", [])
        for field in all_fields:
            prompt += (
                f"- 字段名: {field.get('field_name')}\n"
                f"  类型: {field.get('field_type')}\n"
                f"  空值率: {field.get('null_rate')}\n"
                f"  唯一值数: {field.get('unique_count')}\n"
                f"  样例数据: {field.get('sample_data')}\n"
            )

        prompt += "\n请生成JSON返回，且每个字段必须包含 field_name。"
        return prompt

    def _build_field_relations_system_prompt(self) -> str:
        return (
            "你是资深数据建模专家。请分析两个表之间的字段关系，仅返回有实际业务价值的关联。\n"
            "必须排除无业务意义或弱意义的字段关系，例如 is_delete、deleted、create_time、created_at、update_time、updated_at、timestamp 等系统/审计时间字段。\n"
            "输出必须是JSON数组，不要markdown。每项格式：\n"
            "{\n"
            "  \"source_field\": \"源字段名\",\n"
            "  \"target_field\": \"目标字段名\",\n"
            "  \"relation_type\": \"foreign_key|reference|business_key\",\n"
            "  \"relation_description\": \"简明业务说明\",\n"
            "  \"confidence\": 0.0\n"
            "}\n"
            "如果没有高价值关联，返回 []。"
        )

    def _build_field_relations_user_prompt(self, data: Dict[str, Any]) -> str:
        source = data["source"]
        target = data["target"]

        def fields_to_text(fields: List[Dict[str, Any]]) -> str:
            lines = []
            for field in fields:
                lines.append(
                    f"- {field.get('field_name')} ({field.get('field_type')}) | 业务含义: {field.get('business_meaning','')} | 描述: {field.get('field_description','')} | 样例: {field.get('sample_values','')}"
                )
            return "\n".join(lines)

        return (
            "请分析以下两张表之间的业务字段关联关系。\n\n"
            f"源表: {source.get('table_name')}\n"
            f"源表提示: {source.get('table_description','')}\n"
            "源表字段:\n"
            f"{fields_to_text(source.get('fields', []))}\n\n"
            f"目标表: {target.get('table_name')}\n"
            f"目标表提示: {target.get('table_description','')}\n"
            "目标表字段:\n"
            f"{fields_to_text(target.get('fields', []))}\n\n"
            "只返回有业务价值的字段关系JSON数组，禁止返回系统字段时间字段的弱关系。"
        )

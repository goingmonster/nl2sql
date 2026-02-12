import json
import re
from typing import Any, Dict, List, Optional, Tuple, cast

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.services.clickhouse_client import ClickHouseClient
from app.services.postgresql_client import PostgreSQLClient
from app.models.llm_config import LlmConfig
from app.utils.database_field_json_format import ComprehensiveDatabaseJSONEncoder


class ShotTool:
    def __init__(self, llm_config: LlmConfig, db_config: Optional[Any] = None):
        self.llm_config = llm_config
        self.db_config = db_config
        base_url = getattr(llm_config, "base_url", None)
        api_key = getattr(llm_config, "api_key", None)
        self.open_ai_client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url != "https://api.openai.com/v1" else None,
        )
        self.model = str(getattr(llm_config, "model_name", ""))
        self.temperature = float(getattr(llm_config, "temperature", 0.1) or 0.1)
        self.max_tokens = int(getattr(llm_config, "max_tokens", 4000) or 4000)
        self.messages: List[Dict[str, str]] = []
        self.ck_client: Optional[ClickHouseClient] = None

    def chat(self, message: str) -> str:
        self.messages.append({"role": "user", "content": message})
        typed_messages = [cast(ChatCompletionMessageParam, item) for item in self.messages]
        response = self.open_ai_client.chat.completions.create(
            model=self.model,
            messages=typed_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        reply = response.choices[0].message.content or ""
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def create_sql(self, user_input: str, qa_rows: List[Any]) -> Tuple[str, int]:
        prompt = self.build_complete_sql_prompt_by_shot(user_input, qa_rows)
        if not prompt:
            return "", 0
        ai_result = self.chat(prompt)
        sql = self.extract_sql_from_template(ai_result)
        similarity = self.extract_similarity(ai_result)
        return sql, similarity

    def execute_sql(
        self,
        sql: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: int = 20,
    ) -> List[Dict[str, Any]]:
        if not self.db_config:
            raise ValueError("db_config 不能为空")

        sql = self._sanitize_sql_for_execution(sql)
        if not sql:
            raise ValueError("SQL 为空或无效")

        db_type = (getattr(self.db_config, "type", "") or "").lower()
        if db_type in {"pg", "postgres", "postgresql"}:
            return self._execute_pg_sql(sql, parameters=parameters)
        if db_type in {"ck", "clickhouse"}:
            return self._execute_ck_sql(sql, parameters=parameters, timeout=timeout)
        raise ValueError(f"不支持的数据库类型: {db_type}")

    def build_complete_sql_prompt_by_shot(self, user_input: str, qa_rows: List[Any]) -> str:
        shots = self._to_shots(qa_rows)
        prompt_parts: List[str] = []

        prompt_parts.append(
            """🎯 你是一个 SQL 查询匹配专家

任务：分析用户的问题，从提供的示例中找到最相似的查询，并参考其 SQL 结构生成新的查询语句。

工作原则：
1. 仔细分析用户问题的意图、时间范围、查询对象等信息
2. 从提供的示例中找到最相似的查询模式
3. 参考匹配示例的 SQL 结构，但要适应用户的具体需求
4. 如果没有完全匹配的示例，可以结合多个相似示例的模式"""
        )

        prompt_parts.append("\n📝 【用户问题】")
        prompt_parts.append(user_input)

        if shots:
            prompt_parts.append("\n📚 【SQL 查询示例库】")
            prompt_parts.append("=" * 60)
            prompt_parts.append("请仔细分析以下所有示例，找到与用户问题最相似的查询模式：\n")

            for i, shot in enumerate(shots, 1):
                question = shot.get("question", "")
                sql = shot.get("sql", "")
                where_conditions = shot.get("where_conditions", [])

                prompt_parts.append(f"\n🔸 示例 {i}:")
                prompt_parts.append(f"问题: {question}")
                prompt_parts.append(f"SQL:\n{sql}")

                if where_conditions:
                    prompt_parts.append("WHERE 条件结构:")
                    for condition in where_conditions:
                        field = condition.get("field", "")
                        operator = condition.get("operator", "")
                        value = condition.get("value", "")
                        description = condition.get("description", "")
                        prompt_parts.append(f"  - {field} {operator} '{value}'  // {description}")

                prompt_parts.append("-" * 40)
        else:
            return ""

        prompt_parts.append(
            """
📤 【输出要求】
请分析用户问题与示例的相似性，然后按照以下格式返回：

【相似度】
95

【SQL】
SELECT COUNT(DISTINCT aircraft_icao), COUNT(1)
FROM dws_aircraft_flight_line_tmp
WHERE day_key = '2025-12-06' AND aircraft_model LIKE '%C-17%'

【匹配说明】
选择了示例2，相似度95%，因为都是关于特定飞机型号的统计分析。将示例中的日期'2025-12-06'和机型'C-17'替换为用户问题中的具体参数。

注意：
1. 【相似度】必须是0-100之间的整数，表示用户问题与最相似示例的匹配程度
2. 【SQL】部分必须是完整的可执行查询语句
3. 【匹配说明】简要说明选择了哪个示例、相似度评分及修改原因
4. 相似度90分以上为高度匹配，70-89分为中等匹配，70分以下为低度匹配
"""
        )
        return "\n".join(prompt_parts)

    def extract_similarity(self, ai_response: str) -> int:
        similarity_pattern = r"【相似度】\s*(\d+)"
        similarity_match = re.search(similarity_pattern, ai_response, re.S | re.M)
        if similarity_match:
            try:
                similarity = int(similarity_match.group(1))
                return max(0, min(100, similarity))
            except ValueError:
                pass

        match_desc_pattern = r"相似度(\d+)%"
        match_match = re.search(match_desc_pattern, ai_response, re.S | re.M)
        if match_match:
            try:
                similarity = int(match_match.group(1))
                return max(0, min(100, similarity))
            except ValueError:
                pass

        percent_pattern = r"(\d{1,3})%"
        percent_match = re.search(percent_pattern, ai_response, re.S | re.M)
        if percent_match:
            try:
                similarity = int(percent_match.group(1))
                if 0 <= similarity <= 100:
                    return similarity
            except ValueError:
                pass

        return 0

    def extract_sql_from_template(self, ai_response: str) -> str:
        sql_pattern = r"【SQL】\s*(.*?)\s*【匹配说明】"
        sql_match = re.search(sql_pattern, ai_response, re.S | re.M)
        if sql_match:
            return self._clean_sql(sql_match.group(1).strip())

        alt_sql_pattern = r"【SQL】\s*(.*?)(?:【|$)"
        alt_match = re.search(alt_sql_pattern, ai_response, re.S | re.M)
        if alt_match:
            return self._clean_sql(alt_match.group(1).strip())

        code_block_pattern = r"```sql\s*(.*?)\s*```"
        code_match = re.search(code_block_pattern, ai_response, re.S | re.M | re.IGNORECASE)
        if code_match:
            return self._clean_sql(code_match.group(1).strip())

        any_code_pattern = r"```\s*(.*?)\s*```"
        any_match = re.search(any_code_pattern, ai_response, re.S | re.M)
        if any_match:
            content = any_match.group(1).strip()
            if content.upper().startswith("SELECT") or content.upper().startswith("WITH") or "FROM" in content.upper():
                return self._clean_sql(content)

        lines = ai_response.split("\n")
        for line in lines:
            line = line.strip()
            if line.upper().startswith("SELECT") or line.upper().startswith("WITH"):
                return self._clean_sql(line)
        return ""

    def _clean_sql(self, sql: str) -> str:
        if not sql:
            return ""
        sql = re.sub(r"```sql|```", "", sql, flags=re.IGNORECASE)
        lines = [line.strip() for line in sql.split("\n") if line.strip()]
        if len(lines) > 3:
            return "\n".join(lines)
        return " ".join(lines)

    def _sanitize_sql_for_execution(self, sql: str) -> str:
        cleaned = self._clean_sql(sql)
        cleaned = re.sub(r"^\s*sql\s*[:：]\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()
        while cleaned.endswith(";"):
            cleaned = cleaned[:-1].rstrip()
        return cleaned

    def _to_shots(self, qa_rows: List[Any]) -> List[Dict[str, Any]]:
        shots: List[Dict[str, Any]] = []
        for row in qa_rows:
            question = getattr(row, "question", None)
            sql = getattr(row, "sql", None)
            where_conditions = getattr(row, "where_conditions", None)
            if isinstance(row, dict):
                question = question or row.get("question")
                sql = sql or row.get("sql")
                where_conditions = where_conditions or row.get("where_conditions")
            if not question or not sql:
                continue
            parsed_where = self._parse_where_conditions(where_conditions)
            shots.append(
                {
                    "question": str(question),
                    "sql": str(sql),
                    "where_conditions": parsed_where,
                }
            )
        return shots

    def _parse_where_conditions(self, where_conditions: Any) -> List[Dict[str, Any]]:
        if where_conditions is None:
            return []
        if isinstance(where_conditions, list):
            return [item for item in where_conditions if isinstance(item, dict)]
        if isinstance(where_conditions, str):
            try:
                parsed = json.loads(where_conditions)
                if isinstance(parsed, list):
                    return [item for item in parsed if isinstance(item, dict)]
            except json.JSONDecodeError:
                return []
        return []

    def _execute_pg_sql(self, sql: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        cfg = self.db_config
        if cfg is None:
            raise ValueError("db_config 不能为空")
        client = PostgreSQLClient(
            host=cfg.ip,
            port=cfg.port,
            user=cfg.username,
            password=cfg.password,
            database=cfg.database_name,
        )
        result = client.execute_sql(sql, parameters=parameters)
        if not result.get("success"):
            raise RuntimeError(f"SQL执行错误: {result.get('error')}")
        data = (result.get("result") or {}).get("data") or []
        return self._to_jsonable(data)

    def _execute_ck_sql(
        self,
        sql: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: int = 20,
    ) -> List[Dict[str, Any]]:
        cfg = self.db_config
        if cfg is None:
            raise ValueError("db_config 不能为空")

        if self.ck_client is None:
            self.ck_client = ClickHouseClient(
                host=cfg.ip,
                port=cfg.port,
                username=cfg.username,
                password=cfg.password,
                database=cfg.database_name,
            )

        result = self.ck_client.execute_sql(sql, parameters=parameters, timeout=timeout)
        print(result)
        if not result.get("success"):
            raise RuntimeError(f"SQL执行错误: {result.get('error')}")
        data = (result.get("result") or {}).get("data") or []
        columns = (result.get("result") or {}).get("columns") or []
        if columns:
            zipped = [dict(zip(columns, row)) for row in data]
            return self._to_jsonable(zipped)
        return self._to_jsonable(data)

    def close(self) -> None:
        if self.ck_client:
            try:
                self.ck_client.close()
            finally:
                self.ck_client = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _to_jsonable(self, data: Any) -> Any:
        return json.loads(json.dumps(data, cls=ComprehensiveDatabaseJSONEncoder, ensure_ascii=False))

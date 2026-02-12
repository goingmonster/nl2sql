import time
import uuid
from typing import Dict, Any, Optional

import clickhouse_connect


class ClickHouseClient:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
        settings: Optional[Dict[str, Any]] = None,
    ):
        self.host = host
        self.port = int(port)
        self.username = username
        self.password = password
        self.database = database
        self.settings = settings or {}
        self.client = None
        self.session_id: Optional[str] = None
        self._connect()

    def _connect(self, timeout: int = 20) -> None:
        try:
            self.session_id = f"session_{uuid.uuid4().hex[:8]}_{int(time.time())}"
            merged_settings = {"session_id": self.session_id}
            merged_settings.update(self.settings)
            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                database=self.database,
                connect_timeout=5,
                send_receive_timeout=timeout,
                settings=merged_settings,
            )
        except Exception as e:
            raise Exception(f"ClickHouse连接失败: {e}")

    def execute_sql(self, sql: str, parameters: Dict[str, Any] = None, timeout: int = 20) -> Dict[str, Any]:
        if not self.client:
            self._connect(timeout=timeout)

        start_time = time.time()
        try:
            result = self.client.query(sql, parameters)
            data = result.result_rows
            columns = getattr(result, "column_names", None) or []
            execution_time = round(time.time() - start_time, 3)

            return {
                "success": True,
                "result": {
                    "data": data,
                    "columns": columns,
                    "row_count": len(data),
                    "execution_time": execution_time,
                },
                "error": None,
                "sql": sql,
                "session_id": self.session_id,
                "timeout": False,
            }
        except Exception as e:
            execution_time = round(time.time() - start_time, 3)
            return {
                "success": False,
                "result": None,
                "error": f"SQL执行错误 (session={self.session_id}): {str(e)}",
                "sql": sql,
                "session_id": self.session_id,
                "timeout": False,
                "execution_time": execution_time,
            }

    def close(self) -> None:
        if self.client:
            try:
                self.client.close()
            finally:
                self.client = None

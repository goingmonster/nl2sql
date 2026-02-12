import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

import psycopg2
import psycopg2.extras


def json_serializable(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (list, tuple)):
        return [json_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {key: json_serializable(value) for key, value in obj.items()}
    return obj


class PostgreSQLClient:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.database = database

    def _get_connection(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            connect_timeout=30,
        )

    def execute_sql(self, sql: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            start_time = time.time()
            if parameters:
                cursor.execute(sql, parameters)
            else:
                cursor.execute(sql)
            execution_time = round(time.time() - start_time, 3)

            if cursor.description:
                rows = cursor.fetchall()
                result_data = [json_serializable(dict(row)) for row in rows]
            else:
                result_data = []

            affected_rows = cursor.rowcount if cursor.rowcount >= 0 else 0
            conn.commit()

            return {
                "success": True,
                "result": {
                    "data": result_data,
                    "row_count": len(result_data),
                    "affected_rows": affected_rows,
                    "execution_time": execution_time,
                },
                "error": None,
                "sql": sql,
            }
        except Exception as e:
            if conn:
                conn.rollback()
            return {
                "success": False,
                "result": None,
                "error": str(e),
                "sql": sql,
            }
        finally:
            if conn:
                conn.close()

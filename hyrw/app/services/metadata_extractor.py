import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from sqlalchemy import text
from sqlalchemy.orm import Session
import psycopg2
from clickhouse_connect import get_client
from app.models.nlsql_task_config import NlsqlTaskConfig
from app.models.db_config import DbConfig
from app.models.table_metadata_extended import (
    TableMetadataBasic,
    TableSampleData,
    TableFieldMetadata
)
from app.utils.database_field_json_format import ComprehensiveDatabaseJSONEncoder

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """元数据提取器，支持PostgreSQL和ClickHouse数据库（同步版本）"""

    def __init__(self, db):
        self.db = db

    def extract_metadata_by_task_id(self, task_id: int) -> Dict:
        """
        通过 task_id 提取所有选中表的元数据
        """
        try:
            # 1. 获取 NLSQL 任务配置 - 使用同步查询
            from app.models.nlsql_task_config import NlsqlTaskConfig
            task = self.db.query(NlsqlTaskConfig).filter(NlsqlTaskConfig.id == task_id).first()
            if not task:
                raise ValueError(f"NLSQL任务不存在: {task_id}")

            # 2. 获取数据库配置 - 使用同步查询
            from app.models.db_config import DbConfig
            db_config = self.db.query(DbConfig).filter(DbConfig.id == task.db_config_id).first()
            if not db_config:
                raise ValueError(f"数据库配置不存在: {task.db_config_id}")

            # 3. 获取选中的表列表
            select_tables = task.select_tables or []
            if not select_tables:
                raise ValueError(f"任务 {task_id} 没有选中任何表")

            # 4. 根据不同格式的 select_tables 处理
            extracted_tables = []

            # 如果是数字列表，说明是 table_metadata ID，需要先查询表名
            if all(isinstance(x, int) for x in select_tables):
                # 查询 table_metadata 获取表信息
                from app.models.table_metadata import TableMetadata
                existing_tables = self.db.query(TableMetadata).filter(TableMetadata.id.in_(select_tables)).all()

                for tbl in existing_tables:
                    schema_name = db_config.schema_name or db_config.database_name or 'public'
                    table_name = tbl.table_name

                    # 根据数据库类型提取元数据
                    if db_config.type.lower() in ["postgresql", "pg"]:
                        metadata = self._extract_postgresql_metadata(
                            task_id, db_config, schema_name, table_name
                        )
                    elif db_config.type.lower() in ["clickhouse", "ck"]:
                        metadata = self._extract_clickhouse_metadata(
                            task_id, db_config, schema_name, table_name
                        )
                    else:
                        raise ValueError(f"不支持的数据库类型: {db_config.type}")

                    extracted_tables.append(metadata)

            # 如果是字符串或字典列表，按原来的逻辑处理
            else:
                for table_info in select_tables:
                    # table_info 可能是字符串格式 "schema.table" 或字典格式
                    if isinstance(table_info, str):
                        if '.' in table_info:
                            schema_name, table_name = table_info.split('.', 1)
                        else:
                            schema_name = db_config.schema_name or db_config.database_name or 'public'
                            table_name = table_info
                    elif isinstance(table_info, dict):
                        schema_name = table_info.get('schema', db_config.schema_name or db_config.database_name or 'public')
                        table_name = table_info.get('table')
                    else:
                        continue

                    # 根据数据库类型提取元数据
                    if db_config.type.lower() in ["postgresql", "pg"]:
                        metadata = self._extract_postgresql_metadata(
                            task_id, db_config, schema_name, table_name
                        )
                    elif db_config.type.lower() in ["clickhouse", "ck"]:
                        metadata = self._extract_clickhouse_metadata(
                            task_id, db_config, schema_name, table_name
                        )
                    else:
                        raise ValueError(f"不支持的数据库类型: {db_config.type}")

                    extracted_tables.append(metadata)

            # 5. 更新任务状态为"提取元数据"
            task.status = 2
            self.db.commit()

            return {
                "task_id": task_id,
                "db_config_id": task.db_config_id,
                "extracted_tables": extracted_tables,
                "total_tables": len(extracted_tables)
            }

        except Exception as e:
            logger.error(f"提取任务元数据失败: {str(e)}")
            self.db.rollback()
            raise

    def _extract_postgresql_metadata(
        self, task_id: int, db_config: DbConfig, schema_name: str, table_name: str
    ) -> Dict:
        """
        提取PostgreSQL表的元数据并保存到数据库
        """
        # 建立数据库连接
        conn = psycopg2.connect(
            host=db_config.ip,
            port=db_config.port,
            user=db_config.username,
            password=db_config.password,
            database=db_config.database_name
        )
        conn.autocommit = True
        cursor = conn.cursor()

        try:
            # 1. 获取表的基础信息和DDL
            table_info = self._get_pg_table_info(cursor, schema_name, table_name)

            # 2. 获取表的行数
            row_count = self._get_pg_row_count(cursor, schema_name, table_name)

            # 3. 获取字段信息
            fields_info = self._get_pg_fields_info(cursor, schema_name, table_name)

            # 4. 获取样例数据
            sample_data = self._get_pg_sample_data(cursor, schema_name, table_name)

            # 5. 计算字段的统计信息
            field_stats = self._calculate_pg_field_stats(cursor, schema_name, table_name, fields_info)

            # 6. 保存到数据库
            metadata_dict = {
                "table_info": {
                    **table_info,
                    "row_count": row_count
                },
                "fields_info": fields_info,
                "sample_data": sample_data,
                "field_stats": field_stats
            }

            self._save_metadata_to_db(
                task_id=task_id,
                db_config_id=db_config.id,
                schema_name=schema_name,
                table_name=table_name,
                metadata=metadata_dict
            )

            return metadata_dict

        finally:
            cursor.close()
            conn.close()

    def _extract_clickhouse_metadata(
        self, task_id: int, db_config: DbConfig, schema_name: str, table_name: str
    ) -> Dict:
        """
        提取ClickHouse表的元数据并保存到数据库
        """
        # 建立ClickHouse连接
        client = get_client(
            host=db_config.ip,
            port=db_config.port,
            username=db_config.username,
            password=db_config.password,
            database=db_config.database_name
        )

        try:
            # 1. 获取表的基础信息和DDL
            table_info = self._get_ck_table_info(client, schema_name, table_name)

            # 2. 获取表的行数
            row_count = self._get_ck_row_count(client, schema_name, table_name)

            # 3. 获取字段信息
            fields_info = self._get_ck_fields_info(client, schema_name, table_name)

            # 4. 获取样例数据
            sample_data = self._get_ck_sample_data(client, schema_name, table_name)

            # 5. 计算字段的统计信息
            field_stats = self._calculate_ck_field_stats(client, schema_name, table_name, fields_info)

            # 6. 保存到数据库
            metadata_dict = {
                "table_info": {
                    **table_info,
                    "row_count": row_count
                },
                "fields_info": fields_info,
                "sample_data": sample_data,
                "field_stats": field_stats
            }

            self._save_metadata_to_db(
                task_id=task_id,
                db_config_id=db_config.id,
                schema_name=schema_name,
                table_name=table_name,
                metadata=metadata_dict
            )

            return metadata_dict

        finally:
            client.close()

    # 以下方法保持不变，只删除 async 关键字
    def _get_pg_table_info(self, cursor, schema_name: str, table_name: str) -> Dict:
        """
        获取PostgreSQL表的基础信息和DDL
        """
        # 获取表的DDL
        ddl_query = f"""
        SELECT
            'CREATE TABLE ' || t.table_name || ' (' ||
            array_to_string(
                array_agg(
                    c.column_name || ' ' ||
                    c.data_type ||
                    CASE
                        WHEN c.character_maximum_length IS NOT NULL
                        THEN '(' || c.character_maximum_length || ')'
                        ELSE ''
                    END ||
                    CASE WHEN c.is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END
                )
                , E'\n    '
            ) ||
            ');' as ddl
        FROM information_schema.tables t
        JOIN information_schema.columns c ON t.table_name = c.table_name
        WHERE t.table_schema = '{schema_name}' AND t.table_name = '{table_name}'
        GROUP BY t.table_name
        """

        cursor.execute(ddl_query)
        ddl_result = cursor.fetchone()
        ddl = ddl_result[0] if ddl_result else None

        # 获取表类型（如果有分区表等信息）
        table_type = "regular"  # 默认为普通表

        return {
            "schema_name": schema_name,
            "table_name": table_name,
            "table_ddl": ddl,
            "table_type": table_type
        }

    def _get_pg_row_count(self, cursor, schema_name: str, table_name: str) -> int:
        """
        获取PostgreSQL表的行数
        """
        cursor.execute(f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"')
        return cursor.fetchone()[0]

    def _get_pg_fields_info(self, cursor, schema_name: str, table_name: str) -> List[Dict]:
        """
        获取PostgreSQL表的字段信息
        """
        query = f"""
        SELECT
            column_name,
            data_type,
            is_nullable,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = '{schema_name}' AND table_name = '{table_name}'
        ORDER BY ordinal_position
        """

        cursor.execute(query)
        columns = cursor.fetchall()

        fields = []
        for col in columns:
            fields.append({
                "field_name": col[0],
                "field_type": col[1],
                "is_nullable": col[2] == "YES",
                "max_length": col[3]
            })

        return fields

    def _get_pg_sample_data(self, cursor, schema_name: str, table_name: str, limit: int = 20) -> List[Dict]:
        """
        获取PostgreSQL表的样例数据
        """
        cursor.execute(f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT {limit}')
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        sample_data = []
        for row in rows:
            record = dict(zip(columns, row))
            # 处理None值
            for key, value in record.items():
                if value is None:
                    record[key] = ""
            sample_data.append(record)

        return sample_data

    def _calculate_pg_field_stats(self, cursor, schema_name: str, table_name: str, fields_info: List[Dict]) -> List[Dict]:
        """
        计算PostgreSQL表的字段统计信息
        """
        stats = []

        for field in fields_info:
            field_name = field["field_name"]
            field_type = field.get("field_type", "").lower()

            # PostgreSQL字段名处理 - 检查是否需要引号
            special_chars = '+-*/%<>=&|()[]{}.,;:\'"'
            quoted_field_name = f'"{field_name}"' if any(c in field_name for c in special_chars) else field_name

            # 计算空值率
            null_count_query = f"""
            SELECT
                COUNT(*) as total_count,
                COUNT({quoted_field_name}) as not_null_count
            FROM "{schema_name}"."{table_name}"
            """
            cursor.execute(null_count_query)
            total_count, not_null_count = cursor.fetchone()
            null_rate = (total_count - not_null_count) / total_count if total_count > 0 else 0

            # 计算唯一值数量 - 针对不同类型使用不同方法
            unique_count = 0
            if "json" in field_type or "jsonb" in field_type:
                # JSON/jsonb 类型：使用字符串形式计算唯一值
                try:
                    unique_query = f'SELECT COUNT(DISTINCT {quoted_field_name}::text) FROM "{schema_name}"."{table_name}" WHERE {quoted_field_name} IS NOT NULL'
                    cursor.execute(unique_query)
                    unique_count = cursor.fetchone()[0]
                except Exception:
                    # 如果转换失败，使用近似值
                    unique_count = 0
            elif "array" in field_type:
                # 数组类型：使用近似值或者跳过
                try:
                    unique_query = f'SELECT COUNT(DISTINCT array_to_string({quoted_field_name}, \',\')) FROM "{schema_name}"."{table_name}" WHERE {quoted_field_name} IS NOT NULL'
                    cursor.execute(unique_query)
                    unique_count = cursor.fetchone()[0]
                except Exception:
                    unique_count = 0
            else:
                # 普通类型
                try:
                    unique_query = f'SELECT COUNT(DISTINCT {quoted_field_name}) FROM "{schema_name}"."{table_name}"'
                    cursor.execute(unique_query)
                    unique_count = cursor.fetchone()[0]
                except Exception as e:
                    logger.warning(f"Failed to count unique values for field {field_name}: {str(e)}")
                    unique_count = 0

            # 获取字段的样例数据 - 针对不同类型使用不同方法
            sample_values = []
            try:
                if "json" in field_type or "jsonb" in field_type:
                    # JSON 类型：转换为文本
                    sample_query = f'''
                    SELECT {quoted_field_name}::text
                    FROM "{schema_name}"."{table_name}"
                    WHERE {quoted_field_name} IS NOT NULL
                    LIMIT 20
                    '''
                elif "array" in field_type:
                    # 数组类型：转换为字符串
                    sample_query = f'''
                    SELECT array_to_string({quoted_field_name}, ',')
                    FROM "{schema_name}"."{table_name}"
                    WHERE {quoted_field_name} IS NOT NULL
                    LIMIT 20
                    '''
                else:
                    # 普通类型
                    sample_query = f'''
                    SELECT {quoted_field_name}
                    FROM "{schema_name}"."{table_name}"
                    WHERE {quoted_field_name} IS NOT NULL
                    LIMIT 20
                    '''

                cursor.execute(sample_query)
                sample_values = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                logger.warning(f"Failed to get sample data for field {field_name}: {str(e)}")
                sample_values = []

            stats.append({
                "field_name": field_name,
                "null_rate": float(null_rate),
                "unique_count": unique_count,
                "sample_values": sample_values
            })

        return stats

    def _get_ck_table_info(self, client, schema_name: str, table_name: str) -> Dict:
        """
        获取ClickHouse表的基础信息和DDL
        """
        # 获取表的DDL
        ddl_query = f"SHOW CREATE TABLE `{schema_name}`.`{table_name}`"
        ddl_result = client.query(ddl_query)
        # 修复ClickHouse客户端的结果访问方式
        has_results = hasattr(ddl_result, 'result_rows') and ddl_result.result_rows
        ddl = ddl_result.result_rows[0][0] if has_results else None

        # 获取表引擎信息
        engine_query = f"""
        SELECT engine
        FROM system.tables
        WHERE database = '{schema_name}' AND name = '{table_name}'
        """
        engine_result = client.query(engine_query)
        has_engine_results = hasattr(engine_result, 'result_rows') and engine_result.result_rows
        engine = engine_result.result_rows[0][0] if has_engine_results else "unknown"

        return {
            "schema_name": schema_name,
            "table_name": table_name,
            "table_ddl": ddl,
            "table_type": engine.lower()
        }

    def _get_ck_row_count(self, client, schema_name: str, table_name: str) -> int:
        """
        获取ClickHouse表的行数
        """
        query = f"SELECT COUNT(*) FROM `{schema_name}`.`{table_name}`"
        result = client.query(query)
        # 修复ClickHouse客户端的结果访问方式
        return result.result_rows[0][0] if result.result_rows else 0

    def _get_ck_fields_info(self, client, schema_name: str, table_name: str) -> List[Dict]:
        """
        获取ClickHouse表的字段信息
        """
        query = f"""
        SELECT
            name,
            type,
            default_kind
        FROM system.columns
        WHERE database = '{schema_name}' AND table = '{table_name}'
        ORDER BY position
        """

        result = client.query(query)
        fields = []

        for row in result.result_rows:
            fields.append({
                "field_name": row[0],
                "field_type": row[1],
                "default_kind": row[2]
            })

        return fields

    def _get_ck_sample_data(self, client, schema_name: str, table_name: str, limit: int = 20) -> List[Dict]:
        """
        获取ClickHouse表的样例数据
        """
        query = f"SELECT * FROM `{schema_name}`.`{table_name}` LIMIT {limit}"
        result = client.query(query)

        sample_data = []
        for row in result.result_rows:
            record = dict(zip(result.column_names, row))
            # 处理None值
            for key, value in record.items():
                if value is None:
                    record[key] = ""
            sample_data.append(record)

        return sample_data

    def _calculate_ck_field_stats(self, client, schema_name: str, table_name: str, fields_info: List[Dict]) -> List[Dict]:
        """
        计算ClickHouse表的字段统计信息
        """
        stats = []

        # 先获取表的总行数
        total_query = f"SELECT COUNT(*) FROM `{schema_name}`.`{table_name}`"
        total_result = client.query(total_query)
        # 修复ClickHouse客户端的结果访问方式
        total_count = total_result.result_rows[0][0] if total_result.result_rows else 0

        for field in fields_info:
            field_name = field["field_name"]
            field_type = field.get("field_type", "String").lower()

            # ClickHouse中特殊字符字段名处理 - 如果包含特殊字符，需要用反引号包裹
            # 检查字段名是否包含需要转义的字符
            special_chars = '+-*/%<>=&|()[]{}.,;:\'"'
            quoted_field_name = f"`{field_name}`" if any(c in field_name for c in special_chars) else field_name

            # 判断是否为字符串类型
            is_string_type = any(str_type in field_type for str_type in ['string', 'fixedstring', 'text'])

            # 计算空值率 - 根据字段类型使用不同的空值判断
            if is_string_type:
                null_count_query = f"""
                SELECT countIf({quoted_field_name} IS NULL OR {quoted_field_name} = '') as null_count
                FROM `{schema_name}`.`{table_name}`
                """
            else:
                null_count_query = f"""
                SELECT countIf({quoted_field_name} IS NULL) as null_count
                FROM `{schema_name}`.`{table_name}`
                """

            try:
                null_result = client.query(null_count_query)
                # 修复ClickHouse客户端的结果访问方式
                null_count = null_result.result_rows[0][0] if null_result.result_rows else 0
            except Exception as e:
                logger.warning(f"Failed to count null values for field {field_name}: {str(e)}")
                null_count = 0
            null_rate = null_count / total_count if total_count > 0 else 0

            # 计算唯一值数量
            try:
                # 检查字段类型，使用不同的唯一值计算方法
                if any(special_type in field_type for special_type in ['json', 'array', 'nested', 'tuple', 'geo']):
                    # 对于复杂类型，使用近似值
                    unique_query = f"SELECT length(groupUniqArray({quoted_field_name})) FROM `{schema_name}`.`{table_name}`"
                else:
                    # 对于简单类型，使用精确计数
                    unique_query = f"SELECT uniqExact({quoted_field_name}) FROM `{schema_name}`.`{table_name}`"
                unique_result = client.query(unique_query)
                # 修复ClickHouse客户端的结果访问方式
                unique_count = unique_result.result_rows[0][0] if unique_result.result_rows else 0
            except Exception as e:
                logger.warning(f"Failed to count unique values for field {field_name}: {str(e)}")
                unique_count = 0

            # 获取字段的样例数据 - 根据字段类型使用不同的空值判断
            if is_string_type:
                sample_query = f"""
                SELECT {quoted_field_name}
                FROM `{schema_name}`.`{table_name}`
                WHERE {quoted_field_name} IS NOT NULL AND {quoted_field_name} != ''
                LIMIT 20
                """
            else:
                sample_query = f"""
                SELECT {quoted_field_name}
                FROM `{schema_name}`.`{table_name}`
                WHERE {quoted_field_name} IS NOT NULL
                LIMIT 20
                """

            try:
                sample_result = client.query(sample_query)
                sample_values = [row[0] for row in sample_result.result_rows]
            except Exception as e:
                # 如果查询失败，返回空列表
                logger.warning(f"Failed to get sample data for field {field_name}: {str(e)}")
                sample_values = []

            stats.append({
                "field_name": field_name,
                "null_rate": float(null_rate),
                "unique_count": unique_count,
                "sample_values": sample_values
            })

        return stats

    def _save_metadata_to_db(
        self,
        task_id: int,
        db_config_id: int,
        schema_name: str,
        table_name: str,
        metadata: Dict
    ) -> None:
        """
        保存提取的元数据到数据库
        """
        try:
            # 1. 保存表基础信息
            from app.models.table_metadata_extended import TableMetadataBasic
            table_info = metadata["table_info"]
            table_metadata = TableMetadataBasic(
                table_task_id=task_id,
                db_connection_id=db_config_id,
                schema_name=schema_name,
                table_name=table_name,
                table_ddl=table_info.get("table_ddl", ""),
                table_row_count=table_info.get("row_count", 0),
                table_description="",  # 初始为空，等待人工填写
                table_type=table_info.get("table_type", ""),
                is_active=True
            )
            self.db.add(table_metadata)
            self.db.flush()  # 获取ID

            # 2. 保存样例数据
            from app.models.table_metadata_extended import TableSampleData
            sample_data = TableSampleData(
                table_metadata_id=table_metadata.id,
                sample_data=json.dumps(
                    metadata["sample_data"],
                    ensure_ascii=False,
                    cls=ComprehensiveDatabaseJSONEncoder
                )
            )
            self.db.add(sample_data)

            # 3. 保存字段元数据
            from app.models.table_metadata_extended import TableFieldMetadata
            field_stats = metadata["field_stats"]
            fields_info = metadata["fields_info"]

            for stat in field_stats:
                field_type = next(
                    (f["field_type"] for f in fields_info if f["field_name"] == stat["field_name"]),
                    ""
                )
                field_metadata = TableFieldMetadata(
                    table_metadata_id=table_metadata.id,
                    field_name=stat["field_name"],
                    field_type=field_type,
                    null_rate=stat["null_rate"],
                    sample_data=json.dumps(
                        stat["sample_values"],
                        ensure_ascii=False,
                        cls=ComprehensiveDatabaseJSONEncoder
                    ),
                    unique_count=stat["unique_count"],
                    field_description=""  # 初始为空，等待人工填写
                )
                self.db.add(field_metadata)

            self.db.commit()
            logger.info(f"成功保存表 {schema_name}.{table_name} 的元数据")

        except Exception as e:
            self.db.rollback()
            logger.error(f"保存元数据失败: {str(e)}")
            raise
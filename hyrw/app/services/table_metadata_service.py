import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import db_config, table_metadata
from app.schemas.table_metadata import TableMetadataScanResponse
from app.models.db_config import DbConfig

logger = logging.getLogger(__name__)


class TableMetadataService:
    def __init__(self):
        # 数据库驱动导入
        try:
            import psycopg2
            self.psycopg2 = psycopg2
        except ImportError:
            self.psycopg2 = None
            logger.warning("psycopg2-binary not installed")

        try:
            import clickhouse_connect
            self.clickhouse_connect = clickhouse_connect
        except ImportError:
            self.clickhouse_connect = None
            logger.warning("clickhouse-connect not installed")

    async def scan_tables(self, db: AsyncSession, db_config_id: int) -> TableMetadataScanResponse:
        """扫描数据库表"""
        # 1. 验证db_config是否存在
        db_config_obj = await db_config.crud_db_config.get(db, db_config_id)
        if not db_config_obj:
            return TableMetadataScanResponse(
                success=False,
                message=f"数据库配置不存在，ID: {db_config_id}"
            )

        try:
            # 2. 根据数据库类型连接并获取表信息
            if db_config_obj.type.upper() == 'PG':
                table_list = await self._scan_postgresql_tables(db_config_obj)
            elif db_config_obj.type.upper() == 'CK':
                table_list = await self._scan_clickhouse_tables(db_config_obj)
            else:
                return TableMetadataScanResponse(
                    success=False,
                    message=f"暂不支持数据库类型: {db_config_obj.type}"
                )

            # 3. 删除旧的元数据
            await table_metadata.crud_table_metadata.delete_by_db_config_id(db, db_config_id)

            # 4. 批量保存新的元数据
            if table_list:
                await table_metadata.crud_table_metadata.bulk_create_or_update(
                    db, table_list, db_config_id
                )
            print(table_list)
            return TableMetadataScanResponse(
                success=True,
                message=f"扫描完成，共发现 {len(table_list)} 张表"
            )

        except Exception as e:
            logger.error(f"扫描表失败: {str(e)}")
            return TableMetadataScanResponse(
                success=False,
                message=f"扫描失败: {str(e)}"
            )

    async def _scan_postgresql_tables(self, db_config: DbConfig) -> List[Dict[str, Any]]:
        """扫描PostgreSQL表"""
        if not self.psycopg2:
            raise ImportError("请安装 psycopg2-binary")

        connection = None
        try:
            # 使用schema_name，如果为空则使用默认的'public'
            schema_name = db_config.schema_name or 'public'

            # 连接PostgreSQL
            connection = self.psycopg2.connect(
                host=db_config.ip,
                port=db_config.port,
                database=db_config.database_name,
                user=db_config.username,
                password=db_config.password
            )
            cursor = connection.cursor()

            # 获取表的SQL查询（只获取基表，排除系统表）
            query = """
            SELECT
                t.table_name,
                COALESCE(obj_description(c.oid), '') as table_comment,
                COALESCE(s.n_tup_ins + s.n_tup_upd + s.n_tup_del, 0) as row_count
            FROM information_schema.tables t
            LEFT JOIN pg_class c ON c.relname = t.table_name
            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
            LEFT JOIN pg_stat_user_tables s ON s.relname = t.table_name AND s.schemaname = t.table_schema
            WHERE t.table_schema = %s
            AND t.table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            AND t.table_type = 'BASE TABLE'
            """

            cursor.execute(query, (schema_name,))
            rows = cursor.fetchall()

            table_list = []
            for row in rows:
                table_name = row[0]
                table_comment = row[1]
                row_count = row[2] if row[2] and row[2] > 0 else None

                # 获取DDL - 获取列信息
                columns_query = f"""
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns
                WHERE table_schema = '{schema_name}'
                AND table_name = '{table_name}'
                ORDER BY ordinal_position
                """

                cursor.execute(columns_query)
                columns_result = cursor.fetchall()

                # 构建DDL
                if columns_result:
                    columns_ddl = []
                    for col in columns_result:
                        col_def = f"{col[0]} {col[1]}"
                        if col[2]:  # character_maximum_length
                            col_def += f"({col[2]})"
                        if col[3] == 'NO':  # is_nullable
                            col_def += " NOT NULL"
                        columns_ddl.append(col_def)

                    table_ddl = f"CREATE TABLE {table_name} (\n    " + ",\n    ".join(columns_ddl) + "\n);"
                else:
                    table_ddl = None

                table_list.append({
                    'table_name': table_name,
                    'table_description': table_comment,
                    'table_row_count': row_count,
                    'table_ddl': table_ddl,
                    'table_type': 'TABLE'
                })

            return table_list

        finally:
            if connection:
                connection.close()

    async def _scan_clickhouse_tables(self, db_config: DbConfig) -> List[Dict[str, Any]]:
        """扫描ClickHouse表"""
        if not self.clickhouse_connect:
            raise ImportError("请安装 clickhouse-connect")

        client = None
        try:
            # 连接ClickHouse
            client = self.clickhouse_connect.get_client(
                host=db_config.ip,
                port=db_config.port,
                database=db_config.database_name,
                username=db_config.username,
                password=db_config.password,
                connect_timeout=5
            )

            # 获取表列表 - 修复查询错误
            query = """
            SELECT
                table,
                sum(rows) as row_count
            FROM system.parts
            WHERE active = 1
            AND database = currentDatabase()
            GROUP BY table
            """

            result = client.query(query)
            table_list = []

            # 转换结果为字典列表
            rows = result.result_rows
            for row in rows:
                table_name = row[0]
                row_count = row[1] if row[1] and row[1] > 0 else None

                # 获取表的注释（从 system.tables 表）
                table_comment = ""
                try:
                    comment_query = f"SELECT comment FROM system.tables WHERE database = currentDatabase() AND table = '{table_name}'"
                    comment_result = client.query(comment_query)
                    if comment_result.result_rows:
                        table_comment = comment_result.result_rows[0][0] or ""
                except:
                    table_comment = ""

                # 获取DDL
                try:
                    ddl_result = client.query(f"SHOW CREATE TABLE `{table_name}`")
                    table_ddl = ddl_result.result_rows[0][0] if ddl_result.result_rows else None
                except:
                    table_ddl = None

                table_list.append({
                    'table_name': table_name,
                    'table_description': table_comment,
                    'table_row_count': row_count,
                    'table_ddl': table_ddl,
                    'table_type': 'TABLE'
                })

            return table_list

        finally:
            if client:
                try:
                    client.close()
                except:
                    pass


table_metadata_service = TableMetadataService()
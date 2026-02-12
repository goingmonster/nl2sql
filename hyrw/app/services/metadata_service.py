import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from app.core.config import settings
from app.services.metadata_extractor import MetadataExtractor

logger = logging.getLogger(__name__)

# 使用同步引擎进行数据库连接
sync_engine = create_engine(
    settings.SQLITE_URL,
    connect_args={"check_same_thread": False}
)
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)


class MetadataService:
    """元数据服务，处理元数据相关的业务逻辑（同步版本）"""

    @staticmethod
    def scan_metadata_by_task_id(task_id: int) -> Dict:
        """
        通过 task_id 扫描并提取元数据
        """
        db = SyncSessionLocal()
        try:
            extractor = MetadataExtractor(db)
            result = extractor.extract_metadata_by_task_id(task_id)
            logger.info(f"成功扫描任务 {task_id} 的元数据，共扫描 {result['total_tables']} 个表")
            return result
        except Exception as e:
            logger.error(f"扫描任务元数据失败: {str(e)}")
            raise
        finally:
            db.close()

    @staticmethod
    def get_metadata_by_task_id(task_id: int) -> Dict:
        """
        通过 task_id 获取已扫描的元数据
        """
        db = SyncSessionLocal()
        try:
            # 获取任务信息
            from app.models.nlsql_task_config import NlsqlTaskConfig
            task = db.query(NlsqlTaskConfig).filter(NlsqlTaskConfig.id == task_id).first()
            if not task:
                raise ValueError(f"任务不存在: {task_id}")

            # 获取表基础元数据列表
            from app.models.table_metadata_extended import TableMetadataBasic
            from sqlalchemy.orm import joinedload

            table_metadata_list = db.query(TableMetadataBasic)\
                .options(
                    joinedload(TableMetadataBasic.table_sample_data),
                    joinedload(TableMetadataBasic.table_field_metadata)
                )\
                .filter(TableMetadataBasic.table_task_id == task_id).all()

            if not table_metadata_list:
                return {
                    "task_id": task_id,
                    "status": task.status,
                    "message": "该任务暂无元数据",
                    "tables": []
                }

            # 组装完整的元数据信息
            tables = []
            for table_metadata in table_metadata_list:
                table_info = {
                    "table_id": table_metadata.id,
                    "schema_name": table_metadata.schema_name,
                    "table_name": table_metadata.table_name,
                    "table_ddl": table_metadata.table_ddl,
                    "table_row_count": table_metadata.table_row_count,
                    "table_description": table_metadata.table_description,
                    "table_type": table_metadata.table_type,
                    "is_active": table_metadata.is_active,
                    "created_at": table_metadata.created_at.isoformat() if table_metadata.created_at else None,
                    "updated_at": table_metadata.updated_at.isoformat() if table_metadata.updated_at else None,
                    "sample_data": table_metadata.table_sample_data[0].sample_data if table_metadata.table_sample_data else None,
                    "field_metadata": [
                        {
                            "field_id": field.id,
                            "field_name": field.field_name,
                            "field_type": field.field_type,
                            "null_rate": field.null_rate,
                            "sample_data": field.sample_data,
                            "unique_count": field.unique_count,
                            "field_description": field.field_description,
                            "created_at": field.created_at.isoformat() if field.created_at else None,
                            "updated_at": field.updated_at.isoformat() if field.updated_at else None,
                        }
                        for field in table_metadata.table_field_metadata
                    ]
                }
                tables.append(table_info)

            return {
                "task_id": task_id,
                "status": task.status,
                "db_config_id": task.db_config_id,
                "total_tables": len(tables),
                "tables": tables
            }

        except Exception as e:
            logger.error(f"获取任务元数据失败: {str(e)}")
            raise
        finally:
            db.close()

    @staticmethod
    def get_table_metadata_detail(table_metadata_id: int):
        """
        获取单个表的详细元数据
        """
        db = SyncSessionLocal()
        try:
            from app.models.table_metadata_extended import TableMetadataBasic
            from sqlalchemy.orm import joinedload

            table_metadata = db.query(TableMetadataBasic)\
                .options(
                    joinedload(TableMetadataBasic.table_sample_data),
                    joinedload(TableMetadataBasic.table_field_metadata)
                )\
                .filter(TableMetadataBasic.id == table_metadata_id).first()

            if not table_metadata:
                return None

            return {
                "table_id": table_metadata.id,
                "task_id": table_metadata.table_task_id,
                "db_config_id": table_metadata.db_connection_id,
                "schema_name": table_metadata.schema_name,
                "table_name": table_metadata.table_name,
                "table_ddl": table_metadata.table_ddl,
                "table_row_count": table_metadata.table_row_count,
                "table_description": table_metadata.table_description,
                "table_type": table_metadata.table_type,
                "is_active": table_metadata.is_active,
                "created_at": table_metadata.created_at.isoformat() if table_metadata.created_at else None,
                "updated_at": table_metadata.updated_at.isoformat() if table_metadata.updated_at else None,
                "sample_data": table_metadata.table_sample_data[0].sample_data if table_metadata.table_sample_data else None,
                "field_metadata": [
                    {
                        "field_id": field.id,
                        "field_name": field.field_name,
                        "field_type": field.field_type,
                        "null_rate": field.null_rate,
                        "sample_data": field.sample_data,
                        "unique_count": field.unique_count,
                        "field_description": field.field_description,
                        "created_at": field.created_at.isoformat() if field.created_at else None,
                        "updated_at": field.updated_at.isoformat() if field.updated_at else None,
                    }
                    for field in table_metadata.table_field_metadata
                ]
            }

        except Exception as e:
            logger.error(f"获取表详细元数据失败: {str(e)}")
            raise
        finally:
            db.close()

    @staticmethod
    def update_table_description(table_metadata_id: int, description: str) -> bool:
        """
        更新表描述
        """
        db = SyncSessionLocal()
        try:
            from app.models.table_metadata_extended import TableMetadataBasic

            table_metadata = db.query(TableMetadataBasic).filter(TableMetadataBasic.id == table_metadata_id).first()
            if not table_metadata:
                raise ValueError(f"表元数据不存在: {table_metadata_id}")

            table_metadata.table_description = description
            db.commit()

            logger.info(f"成功更新表 {table_metadata.schema_name}.{table_metadata.table_name} 的描述")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"更新表描述失败: {str(e)}")
            raise
        finally:
            db.close()

    @staticmethod
    def update_field_description(field_metadata_id: int, description: str) -> bool:
        """
        更新字段描述
        """
        db = SyncSessionLocal()
        try:
            from app.models.table_metadata_extended import TableFieldMetadata

            field_metadata = db.query(TableFieldMetadata).filter(TableFieldMetadata.id == field_metadata_id).first()
            if not field_metadata:
                raise ValueError(f"字段元数据不存在: {field_metadata_id}")

            field_metadata.field_description = description
            db.commit()

            logger.info(f"成功更新字段 {field_metadata.field_name} 的描述")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"更新字段描述失败: {str(e)}")
            raise
        finally:
            db.close()

    @staticmethod
    def delete_table_metadata(table_metadata_id: int) -> bool:
        """
        删除表的元数据（级联删除样例数据和字段元数据）
        """
        db = SyncSessionLocal()
        try:
            from app.models.table_metadata_extended import TableMetadataBasic

            table_metadata = db.query(TableMetadataBasic).filter(TableMetadataBasic.id == table_metadata_id).first()
            if not table_metadata:
                return False

            db.delete(table_metadata)  # 会自动级联删除关联的数据
            db.commit()

            logger.info(f"成功删除表元数据: {table_metadata_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"删除表元数据失败: {str(e)}")
            raise
        finally:
            db.close()
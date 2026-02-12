import base64
import json
import re
import uuid
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Union


class ComprehensiveDatabaseJSONEncoder(json.JSONEncoder):
    """
    全面的数据库字段JSON编码器
    专门处理各种数据库的特有字段类型，最后无法处理才转为字符串
    """

    def default(self, obj):

        # === 基础JSON标准类型 ===
        if isinstance(obj, (int, float, bool, type(None), str)):
            return obj

        # === 数值类型 ===
        elif isinstance(obj, Decimal):
            return str(obj)  # 保持精度

        elif isinstance(obj, complex):
            return {'real': obj.real, 'imag': obj.imag}

        # === 日期时间类型 ===
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return {'days': obj.days, 'seconds': obj.seconds, 'microseconds': obj.microseconds}

        # === 二进制数据类型 ===
        elif isinstance(obj, (bytes, bytearray)):
            return {'__type__': 'binary', 'data': base64.b64encode(obj).decode('ascii')}
        elif isinstance(obj, memoryview):
            return {'__type__': 'memoryview', 'data': base64.b64encode(obj.tobytes()).decode('ascii')}

        # === PostgreSQL特有类型 ===
        elif self._is_postgresql_type(obj):
            return self._encode_postgresql_type(obj)

        # === ClickHouse特有类型 ===
        elif self._is_clickhouse_type(obj):
            return self._encode_clickhouse_type(obj)

        # === MySQL特有类型 ===
        elif self._is_mysql_type(obj):
            return self._encode_mysql_type(obj)

        # === 达梦数据库特有类型 ===
        elif self._is_dameng_type(obj):
            return self._encode_dameng_type(obj)

        # === 地理空间数据类型（通用） ===
        elif self._is_geospatial_type(obj):
            return self._encode_geospatial_type(obj)

        # === 集合类型 ===
        elif isinstance(obj, list):
            return [self.default(item) if not self._is_json_serializable(item) else item for item in obj]
        elif isinstance(obj, tuple):
            return {'__type__': 'tuple', 'data': [self.default(item) if not self._is_json_serializable(item) else item for item in obj]}
        elif isinstance(obj, set):
            return {'__type__': 'set', 'data': [self.default(item) if not self._is_json_serializable(item) else item for item in obj]}

        # === UUID类型 ===
        elif isinstance(obj, uuid.UUID):
            return str(obj)

        # === 字典类型 ===
        elif isinstance(obj, dict):
            return {str(k): self.default(v) if not self._is_json_serializable(v) else v for k, v in obj.items()}

        # === IP地址类型 ===
        elif self._is_ip_type(obj):
            return {'__type__': 'ip', 'value': str(obj)}

        # === 数组类型 ===
        elif hasattr(obj, '__len__') and hasattr(obj, '__getitem__') and not isinstance(obj, (str, bytes, bytearray)):
            return {'__type__': 'array', 'data': [self.default(item) if not self._is_json_serializable(item) else item for item in obj]}

        # === 枚举类型 ===
        elif hasattr(obj, '__class__') and hasattr(obj.__class__, '__members__'):
            return {'__type__': 'enum', 'class': obj.__class__.__name__, 'name': obj.name, 'value': obj.value}

        # === 最后的兜底：转为字符串 ===
        else:
            try:
                return str(obj)
            except Exception:
                return f"<unrepresentable: {type(obj).__name__}>"

    def _is_postgresql_type(self, obj) -> bool:
        """检查是否为PostgreSQL特有类型"""
        try:
            # PostgreSQL特定类型检查
            pg_types = [
                'psycopg2.extras.Json',  # JSON类型
                'psycopg2.extras.Range',  # Range类型
                'psycopg2.extras.NumericRange',  # 数值范围
                'psycopg2.extras.DateTimeRange',  # 日期范围
                'psycopg2.extras.Inet',  # 网络地址类型
                'psycopg2.extras.Cidr',  # CIDR网络地址
                'psycopg2.extras.UUID',  # UUID适配器
                'psycopg2.extensions.Binary',  # 二进制数据
            ]

            obj_class_name = f"{obj.__class__.__module__}.{obj.__class__.__name__}"
            return any(pg_type in obj_class_name for pg_type in pg_types)
        except:
            return False

    def _encode_postgresql_type(self, obj) -> Dict[str, Any]:
        """编码PostgreSQL特有类型"""
        obj_class_name = f"{obj.__class__.__module__}.{obj.__class__.__name__}"

        # JSON类型
        if 'Json' in obj_class_name:
            return {'__type__': 'postgresql_json', 'data': str(obj)}

        # Range类型
        elif 'Range' in obj_class_name:
            return {
                '__type__': 'postgresql_range',
                'lower': self.default(obj.lower) if hasattr(obj, 'lower') else None,
                'upper': self.default(obj.upper) if hasattr(obj, 'upper') else None,
                'lower_inc': getattr(obj, 'lower_inc', None),
                'upper_inc': getattr(obj, 'upper_inc', None),
                'lower_inf': getattr(obj, 'lower_inf', None),
                'upper_inf': getattr(obj, 'upper_inf', None),
                'empty': getattr(obj, 'empty', None)
            }

        # 网络地址类型
        elif 'Inet' in obj_class_name or 'Cidr' in obj_class_name:
            return {'__type__': 'postgresql_network', 'address': str(obj)}

        # 二进制数据
        elif 'Binary' in obj_class_name:
            return {'__type__': 'postgresql_binary', 'data': base64.b64encode(obj).decode('ascii')}

        return {'__type__': 'postgresql_unknown', 'data': str(obj)}

    def _is_clickhouse_type(self, obj) -> bool:
        """检查是否为ClickHouse特有类型"""
        # ClickHouse数组类型检查
        if isinstance(obj, list) and len(obj) > 0:
            # 检查是否为ClickHouse的Array(UInt64)等类型
            return True

        # ClickHouse Tuple类型
        if isinstance(obj, tuple):
            return True

        # ClickHouse Nested类型（可能表现为复杂结构）
        if hasattr(obj, '__dict__') and hasattr(obj.__class__, '__name__'):
            class_name = str(type(obj))
            return any(clickhouse_marker in class_name.lower() for clickhouse_marker in
                      ['clickhouse', 'array', 'nested', 'tuple'])

        return False

    def _encode_clickhouse_type(self, obj) -> Dict[str, Any]:
        """编码ClickHouse特有类型"""
        if isinstance(obj, list):
            return {
                '__type__': 'clickhouse_array',
                'data': [self.default(item) if not self._is_json_serializable(item) else item for item in obj]
            }
        elif isinstance(obj, tuple):
            return {
                '__type__': 'clickhouse_tuple',
                'data': [self.default(item) if not self._is_json_serializable(item) else item for item in obj]
            }
        else:
            return {'__type__': 'clickhouse_complex', 'data': self.default(dict(obj) if hasattr(obj, '__dict__') else str(obj))}

    def _is_mysql_type(self, obj) -> bool:
        """检查是否为MySQL特有类型"""
        try:
            import mysql.connector
            # MySQL特有的数据类型检查
            if hasattr(obj, '__class__'):
                class_name = str(type(obj))
                return any(mysql_marker in class_name.lower() for mysql_marker in
                          ['mysql', 'connector', 'decimal', 'datetime'])
            return False
        except ImportError:
            return False

    def _encode_mysql_type(self, obj) -> Dict[str, Any]:
        """编码MySQL特有类型"""
        return {'__type__': 'mysql_specific', 'data': str(obj)}

    def _is_dameng_type(self, obj) -> bool:
        """检查是否为达梦数据库特有类型"""
        # 达梦数据库特有的数据类型
        if hasattr(obj, '__class__'):
            class_name = str(type(obj))
            return any(dm_marker in class_name.lower() for dm_marker in
                      ['dm', 'dameng', 'datetime', 'timestamp', 'clob', 'blob'])
        return False

    def _encode_dameng_type(self, obj) -> Dict[str, Any]:
        """编码达梦数据库特有类型"""
        class_name = str(type(obj)).lower()

        if 'clob' in class_name or 'blob' in class_name:
            # 大对象类型
            if isinstance(obj, (bytes, bytearray)):
                return {'__type__': 'dameng_lob', 'data': base64.b64encode(obj).decode('ascii')}
            else:
                return {'__type__': 'dameng_lob', 'data': str(obj)}

        return {'__type__': 'dameng_specific', 'data': str(obj)}

    def _is_geospatial_type(self, obj) -> bool:
        """检查是否为地理空间数据类型"""
        # 检查常见的GIS类型
        class_name = str(type(obj)).lower()
        gis_keywords = ['point', 'line', 'polygon', 'geometry', 'geography', 'srid', 'wkb', 'wkt']

        if any(keyword in class_name for keyword in gis_keywords):
            return True

        # 检查坐标格式
        if isinstance(obj, (list, tuple)) and len(obj) >= 2:
            try:
                # 检查是否为坐标格式 [x, y] 或 [lat, lng]
                if all(isinstance(x, (int, float, Decimal)) for x in obj[:2]):
                    x, y = float(obj[0]), float(obj[1])
                    # 经纬度范围检查
                    return (-180 <= x <= 180 and -90 <= y <= 90) or (-90 <= x <= 90 and -180 <= y <= 180)
            except:
                pass

        # 检查字符串格式的GIS数据
        if isinstance(obj, str):
            gis_patterns = [
                r'^SRID=\d+;POINT\s*\(',  # PostGIS格式
                r'^POINT\s*\(',           # WKT点
                r'^LINESTRING\s*\(',      # WKT线
                r'^POLYGON\s*\(',         # WKT面
                r'^\{.*"type".*"coordinates',  # GeoJSON
                r'^\{.*"coordinates".*\}',     # 简化坐标格式
            ]
            return any(re.search(pattern, obj.strip()) for pattern in gis_patterns)

        return False

    def _encode_geospatial_type(self, obj) -> Dict[str, Any]:
        """编码地理空间数据类型"""
        # 坐标数组/元组
        if isinstance(obj, (list, tuple)) and len(obj) >= 2:
            return {
                '__type__': 'coordinates',
                'format': 'array',
                'coords': [float(x) if isinstance(x, (int, float, Decimal)) else str(x) for x in obj],
                'crs': 'EPSG:4326'  # 默认坐标系
            }

        # 字符串格式
        if isinstance(obj, str):
            obj = obj.strip()
            if obj.startswith('SRID='):
                return {'__type__': 'postgis_geometry', 'raw': obj}
            elif obj.startswith('POINT') or obj.startswith('LINESTRING') or obj.startswith('POLYGON'):
                return {'__type__': 'wkt_geometry', 'raw': obj}
            elif '.coordinates' in obj or 'type' in obj:
                return {'__type__': 'geojson_string', 'raw': obj}

        # 对象类型（可能是GIS库的对象）
        if hasattr(obj, '__dict__'):
            attrs = {k: self.default(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
            return {
                '__type__': 'gis_object',
                'class': obj.__class__.__name__,
                'attributes': attrs
            }

        return {'__type__': 'geospatial_string', 'data': str(obj)}

    def _is_ip_type(self, obj) -> bool:
        """检查是否为IP地址类型"""
        try:
            import ipaddress
            return isinstance(obj, (
                ipaddress.IPv4Address, ipaddress.IPv6Address,
                ipaddress.IPv4Network, ipaddress.IPv6Network
            ))
        except ImportError:
            # 简单的IP地址字符串检查
            if isinstance(obj, str):
                ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
                ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
                return bool(re.match(ipv4_pattern, obj) or re.match(ipv6_pattern, obj))
            return False

    def _is_json_serializable(self, obj):
        """检查对象是否可以直接JSON序列化"""
        try:
            json.dumps(obj)
            return True
        except (TypeError, OverflowError, ValueError):
            return False

import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.table_level_prompt import TableLevelPrompt
from app.models.table_field_prompt import TableFieldPrompt
from app.models.nlsql_task_config import NlsqlTaskConfig
from app.models.db_config import DbConfig
from app.models.table_metadata_extended import TableMetadataBasic, TableSampleData, TableFieldMetadata
from app.models.table_field_relation import TableFieldRelation


class GeneratePrompt:
    """生成表选择提示词的类"""

    def __init__(self, db: Session):
        self.db = db
    
    def build_query_context_prompt(
        self,
        user_input: str,
        table_names: List[str],
        task_id: int
    ) -> str:
        """
        构建完整的查询上下文提示词（用于 QueryContextTool）

        Args:
            user_input: 用户输入
            table_names: 相关表名列表
            task_id: PromptGenerationTask 的 ID

        Returns:
            str: 完整的查询上下文提示词
        """
        prompt_parts = []

        prompt_parts.append("=" * 50)
        prompt_parts.append("""
你是一个 Query Context 构建器 🧠。

你的任务是：
- 根据【用户问题】和【已知表信息】，构建一次查询所需的 Query Context。
- 明确字段是用于 WHERE 过滤，还是用于 GROUP BY 分组。

你【不能】：
- 生成 SQL
- 推断或发明字段含义
- 添加未提供的表或 JOIN 关系

你【必须】：
- 严格使用给定的表和 JOIN 事实
- 只做"字段用途分类"，不做 SQL 设计
- 输出必须严格符合下面定义的【行协议】

────────────────
🎯 核心目标
────────────────
为后续 SQL 生成阶段提供【严格、不可歧义】的上下文约束。
    """)

        # ====================== 第一步：获取表提示词 TableLevelPrompt ======================
        table_prompts = {}
        prompts = self.db.query(TableLevelPrompt).filter(
            TableLevelPrompt.task_id == task_id,
            TableLevelPrompt.table_name.in_(table_names),
            TableLevelPrompt.is_active.is_(True),
        ).all()
        for prompt in prompts:
            table_prompts[prompt.table_name] = prompt

        # ====================== 第二步：获取字段样例数据 TableFieldMetadata ======================
        # 需要将 TableMetadataBasic 与 TableFieldMetadata 关联并进行筛选
        table_metadata_map = {}
        table_fields_data = {}

        for table_name in table_names:
            # 获取 TableMetadataBasic（使用task_id过滤）
            metadata = self.db.query(TableMetadataBasic).filter(
                TableMetadataBasic.table_name == table_name,
                TableMetadataBasic.table_task_id == task_id,
            ).first()

            if metadata:
                table_metadata_map[table_name] = metadata

                # 获取 TableFieldMetadata 的字段信息（每个字段只取1行样例数据）
                fields = self.db.query(TableFieldMetadata).filter(
                    TableFieldMetadata.table_metadata_id == metadata.id
                ).all()

                table_fields_data[table_name] = []
                for field in fields:
                    # 解析样例数据，只取1行
                    sample_data = ""
                    if field.sample_data:
                        try:
                            # 尝试解析JSON
                            sample_list = json.loads(field.sample_data)
                            if isinstance(sample_list, list) and sample_list:
                                # 取第一个样例值
                                sample_data = str(sample_list[0])[:100]  # 限制长度
                            else:
                                sample_data = str(field.sample_data)[:100]
                        except (json.JSONDecodeError, Exception):
                            # 更具体的异常处理
                            sample_data = str(field.sample_data)[:100]

                    table_fields_data[table_name].append({
                        'field_name': field.field_name,
                        'field_type': field.field_type,
                        'sample_data': sample_data,
                        'null_rate': field.null_rate,
                        'unique_count': field.unique_count
                    })

        # ====================== 第三步：获取字段提示词 TableFieldPrompt ======================
        field_prompts = {}
        for table_name in table_names:
            if table_name in table_prompts:
                table_prompt = table_prompts[table_name]
                # 获取字段提示词
                field_prompt_list = self.db.query(TableFieldPrompt).filter(
                    TableFieldPrompt.table_level_prompt_id == table_prompt.id
                ).all()

                field_prompts[table_name] = {}
                for fp in field_prompt_list:
                    field_prompts[table_name][fp.field_name] = {
                        'business_meaning': fp.business_meaning or '',
                        'data_format': fp.data_format or '',
                        'field_description': fp.field_description or '',
                        'query_scenarios': fp.query_scenarios or '',
                        'rules': fp.rules or ''
                    }

        # ====================== 第四步：将字段样例数据和提示词进行拼接 ======================
        # 每个字段拼接成一行
        prompt_parts.append("\n\n已选择的数据库表详细信息：")
        prompt_parts.append("=" * 50)

        for table_name in table_names:
            prompt_parts.append(f"\n📋 表：{table_name}")

            # 表级别提示词
            if table_name in table_prompts:
                table_prompt = table_prompts[table_name]
                if table_prompt.table_description:
                    prompt_parts.append(f"表描述：{table_prompt.table_description}")

            # 字段信息 - 样例数据和提示词拼接
            if table_name in table_fields_data and table_name in field_prompts:
                prompt_parts.append("\n字段信息：")
                for field_data in table_fields_data[table_name]:
                    field_name = field_data['field_name']
                    field_prompt = field_prompts[table_name].get(field_name, {})

                    # 拼接一行：字段名（类型）| 样例数据 | 业务含义 | 字段描述
                    field_line_parts = []

                    # 字段名和类型
                    field_line_parts.append(f"{field_name}({field_data.get('field_type', 'unknown')})")

                    # 样例数据
                    if field_data.get('sample_data'):
                        field_line_parts.append(f"样例:{field_data['sample_data']}")

                    # 空值率和唯一值
                    if field_data.get('null_rate') is not None:
                        field_line_parts.append(f"空值率:{field_data['null_rate']:.2%}")
                    if field_data.get('unique_count'):
                        field_line_parts.append(f"唯一值:{field_data['unique_count']}")

                    # 业务含义
                    if field_prompt.get('business_meaning'):
                        field_line_parts.append(f"业务:{field_prompt['business_meaning']}")

                    # 字段描述
                    if field_prompt.get('field_description'):
                        field_line_parts.append(f"说明:{field_prompt['field_description']}")

                    # 拼接成一行
                    field_line = " | ".join(field_line_parts)
                    prompt_parts.append(f"  • {field_line}")

        # 表关系信息
        prompt_parts.append("\n\n表之间的关联关系（JOIN 事实）：")
        prompt_parts.append("(暂无关联关系信息)")

        # 用户输入
        prompt_parts.append("\n" + "=" * 50)
        prompt_parts.append(f"用户输入: {user_input}")

        # 行协议定义
        prompt_parts.append("""
────────────────
⚠️ 强约束输出格式（行协议）
────────────────

【行协议规则】
- 每行一个 KEY=VALUE
- KEY 必须全部大写
- 多个值使用英文逗号分隔
- JOIN 使用 table.column->table.column
- 如果某一项不存在，可以不输出该行
- 严禁输出任何解释性文字或多余内容

允许的 KEY（只能使用这些）：
- ALLOWED_TABLES
- DRIVER_TABLE
- JOIN
- TABLE_USAGE.<table>.WHERE_FIELDS
- TABLE_USAGE.<table>.GROUP_BY_FIELDS
- TABLE_USAGE.<table>.AGG_FIELDS
- TABLE_USAGE.<table>.JOIN_KEY

────────────────
🚨 字段用途强制规则（必须遵守）
────────────────
❗ 1. WHERE_FIELDS：
   - 只包含用于条件过滤的字段
   - 必须与用户问题中的筛选条件一一对应

❗ 2. GROUP_BY_FIELDS：
   - 只包含用于分组维度的字段
   - 如果用户问题出现"按…统计 / 按…分组 / 各…情况"等表达，必须提取对应字段

❗ 3. AGG_FIELDS：
   - 只包含需要被聚合的字段（如计数、求和等）
   - 如果用户问题没有明确聚合需求，可以不输出

❗ 4. 同一个字段不能同时出现在 WHERE_FIELDS 和 GROUP_BY_FIELDS 中
❗ 5. 只允许使用已提供的表和字段

────────────────
📌 输出示例（格式示例，不是业务示例）
────────────────

ALLOWED_TABLES=AAA,BBB,CCC
DRIVER_TABLE=AAA

JOIN=BBB.person_id->AAA.person_id
JOIN=CCC.person_id->AAA.person_id

TABLE_USAGE.AAA.WHERE_FIELDS=rank,start_date
TABLE_USAGE.AAA.GROUP_BY_FIELDS=department
TABLE_USAGE.AAA.JOIN_KEY=person_id

TABLE_USAGE.BBB.WHERE_FIELDS=nationality
TABLE_USAGE.BBB.JOIN_KEY=person_id

TABLE_USAGE.CCC.GROUP_BY_FIELDS=position
TABLE_USAGE.CCC.AGG_FIELDS=incumbency
TABLE_USAGE.CCC.JOIN_KEY=person_id

────────────────
请严格按照上述行协议输出 Query Context。
    """)

        return "\n".join(prompt_parts)


    def build_column_patch_prompt(
        self,
        user_input,
        query_context: Dict[str, Any],
        table_names: List[str],
        task_id: Optional[int] = None,
    ) -> str:
        role_prompt = """
你是一个【SQL WHERE 条件生成器】🧠，只负责生成 WHERE 条件。

🎯 任务目标：
- 根据【用户查询意图】和【RULE 规则】，为【每一个表】分别生成 WHERE 条件。
- 所有 WHERE 条件必须严格遵守 RULE，禁止自行推断或发挥。

────────────────
🚨 强制规则（必须 100% 遵守）
────────────────
❗ 1. 每个表【必须单独输出一段】，禁止多个表合并到同一个 WHERE
❗ 2. 每段 WHERE【只能使用当前表的字段】，严禁跨表字段
❗ 3. 只允许输出 WHERE 子句，禁止输出 SELECT / JOIN / 解释性文字
❗ 4. WHERE 中使用的值【必须来源于用户问题】，禁止编造，推断或假设
❗ 5. 凡 RULE 中涉及【简繁体 / 数字汉字泛化】的要求，无论对象是人名、地名还是组织名，都必须执行  
❗ 6. 必须检查并使用所有适用的 RULE，禁止忽略 RULE  

────────────────
📐 输出格式（格式即协议）
────────────────
✅ 每个表单独一段，段与段之间必须空一行  
✅ 严格使用以下格式，不允许多字或少字：

[TABLE] 表名
WHERE 条件
REASON: 使用了哪些 RULE

────────────────
🛑 兜底规则
────────────────
⚠️ 如果无法为某个表生成合法 WHERE 条件，必须输出：

[TABLE] 表名
WHERE 1=1
REASON: 无可用字段或不满足 RULE

────────────────
📌 再次强调
────────────────
- 表与表之间【完全独立】❌ 不允许共享 WHERE  
- WHERE 中不允许出现不属于该表的字段  
- 不允许遗漏任何适用的 RULE  
    """

        columns_patch_prompt = [role_prompt]

        # 添加用户问题
        columns_patch_prompt.append(f"\n═ 用户问题 ═\n{user_input}")

        table_usage = {}

        # 添加表的使用信息（从query_context中提取）
        if query_context and "table_usage" in query_context:
            table_usage = query_context["table_usage"]
            if table_usage:
                columns_patch_prompt.append("\n═ 表使用信息 ═")
                for table_name in table_names:
                    if table_name in table_usage:
                        usage = table_usage[table_name]
                        columns_patch_prompt.append(f"\n▶ 表：{table_name}")

                        if usage.get("filter_fields"):
                            fields = ", ".join(usage["filter_fields"])
                            columns_patch_prompt.append(f"  过滤字段：{fields}")

                        if usage.get("group_by_fields"):
                            fields = ", ".join(usage["group_by_fields"])
                            columns_patch_prompt.append(f"  分组字段：{fields}")

        # 添加字段详细信息
        if table_names:
            columns_patch_prompt.append("\n═ 字段详细信息 ═")
            for table_name in table_names:
                # 获取该表的字段提示词（按 table_level_prompt 关联过滤）
                relevant_prompts = self.db.query(TableLevelPrompt).filter(
                    TableLevelPrompt.table_name == table_name,
                    TableLevelPrompt.is_active.is_(True)
                )
                if task_id is not None:
                    relevant_prompts = relevant_prompts.filter(TableLevelPrompt.task_id == task_id)
                relevant_prompts = relevant_prompts.all()

                if relevant_prompts:
                    columns_patch_prompt.append(f"\n📋 表：{table_name}")
                    columns_patch_prompt.append("─" * 40)

                    for prompt in relevant_prompts:
                        fields_query = self.db.query(TableFieldPrompt).filter(
                            TableFieldPrompt.table_level_prompt_id == prompt.id
                        )
                        filter_fields = table_usage.get(table_name, {}).get("filter_fields", []) if table_usage else []
                        if filter_fields:
                            fields_query = fields_query.filter(TableFieldPrompt.field_name.in_(filter_fields))
                        fields = fields_query.limit(5).all()  # 限制字段数量

                        for field in fields:
                            columns_patch_prompt.append(f"\n🔹 字段：{field.field_name}")

                            if field.business_meaning:
                                columns_patch_prompt.append(f"  业务含义：{field.business_meaning}")

                            if field.data_format:
                                columns_patch_prompt.append(f"  数据格式：{field.data_format}")

                            if field.field_description:
                                columns_patch_prompt.append(f"  字段描述：{field.field_description}")

                            if field.query_scenarios:
                                scenarios = field.query_scenarios
                                if isinstance(scenarios, list):
                                    columns_patch_prompt.append(f"  查询场景：")
                                    for scenario in scenarios[:3]:
                                        columns_patch_prompt.append(f"    • {scenario}")
                                else:
                                    columns_patch_prompt.append(f"  查询场景：{scenarios}")

                            if field.rules:
                                rules = field.rules
                                if isinstance(rules, list):
                                    columns_patch_prompt.append(f"  规则：")
                                    for rule in rules[:3]:
                                        columns_patch_prompt.append(f"    - {rule}")
                                else:
                                    columns_patch_prompt.append(f"  规则：{rules}")

        # 添加数据库类型说明
        # 尝试获取第一个表的数据库类型
        db_type_prompt = self._get_database_type_prompt(table_names[0], task_id=task_id) if table_names else ""
        if db_type_prompt:
            columns_patch_prompt.append(db_type_prompt)

        columns_patch_prompt.append("\n请根据上述信息，为每个表生成 WHERE 条件。")
        columns_patch_prompt.append("记住：严格遵守输出格式要求！")

        return "\n".join(columns_patch_prompt)

    def _get_database_type_prompt(self, table_name: str, task_id: Optional[int] = None) -> str:
        """
        获取数据库类型的特定提示词

        Args:
            table_name: 表名，用于查找对应的数据库类型

        Returns:
            str: 数据库类型特定的提示词
        """
        if not table_name:
            return ""

        # 通过 table_level_prompt -> nlsql_task_config -> db_config 获取数据库类型
        table_prompt_query = self.db.query(TableLevelPrompt).filter(
            TableLevelPrompt.table_name == table_name,
            TableLevelPrompt.is_active.is_(True)
        )
        if task_id is not None:
            table_prompt_query = table_prompt_query.filter(TableLevelPrompt.task_id == task_id)
        table_prompt = table_prompt_query.first()

        if not table_prompt:
            return ""

        task = self.db.query(NlsqlTaskConfig).filter(
            NlsqlTaskConfig.id == table_prompt.task_id
        ).first()
        if not task:
            return ""

        db_config = self.db.query(DbConfig).filter(
            DbConfig.id == task.db_config_id
        ).first()
        if not db_config or not db_config.type:
            return ""

        db_type = db_config.type

        db_type_lower = str(db_type).lower()

        db_specific_rules = {
            "mysql": "（MySQL提示：字符串比较使用 LIKE 或 =，注意字符集；日期使用 BETWEEN；NULL使用 IS NULL）",
            "postgresql": "（PostgreSQL提示：字符串区分大小写，可使用 ILIKE 进行不区分大小写匹配；支持 >、BETWEEN 等）",
            "oracle": "（Oracle提示：字符串默认不区分大小写；日期使用 TO_DATE 函数；空字符串视为 NULL）",
            "sqlserver": "（SQL Server提示：字符串比较可能不区分大小写；日期使用 BETWEEN；NULL使用 IS NULL）"
        }

        rule = db_specific_rules.get(db_type_lower, "")
        return f"\n═ 数据库类型 ═\n数据库类型：{db_type}{rule}"

    def _get_database_system_prompt(self, database_type: str) -> str:
        """
        获取数据库特定的系统提示词

        Args:
            database_type: 数据库类型

        Returns:
            str: 数据库特定的系统提示词
        """
        db_type_lower = str(database_type).lower()

        system_prompts = {
            "mysql": """你是一个专业的 MySQL 数据库助手，擅长根据用户需求生成高效的 MySQL 查询语句。
特别注意 MySQL 的语法特性：
- 使用 LIMIT 而不是 TOP 来限制结果
- 日期时间函数使用 NOW(), CURDATE()
- 字符串连接使用 CONCAT() 函数
- GROUP BY 需要包含 SELECT 中的非聚合列""",

            "postgresql": """你是一个专业的 PostgreSQL 数据库助手，擅长根据用户需求生成高效的 PostgreSQL 查询语句。
特别注意 PostgreSQL 的语法特性：
- 支持丰富的窗口函数如 ROW_NUMBER(), RANK(), DENSE_RANK()
- 字符串连接使用 || 操作符
- 可以使用 ILIKE 进行不区分大小写的模糊匹配
- 支持数组类型和相关的操作符""",

            "oracle": """你是一个专业的 Oracle 数据库助手，擅长根据用户需求生成高效的 Oracle 查询语句。
特别注意 Oracle 的语法特性：
- 使用 ROWNUM 来限制结果数量
- 日期需要使用 TO_DATE 函数转换
- 字符串连接使用 || 操作符
- 空字符串被视为 NULL""",

            "sqlserver": """你是一个专业的 SQL Server 数据库助手，擅长根据用户需求生成高效的 SQL Server 查询语句。
特别注意 SQL Server 的语法特性：
- 使用 TOP N 来限制结果数量
- 支持 WITH 语句创建公用表表达式(CTE)
- 日期时间函数使用 GETDATE()
- 可以使用 CONCAT() 函数连接字符串""",

            "clickhouse": """你是一个专业的 ClickHouse 数据库助手，擅长根据用户需求生成高效的 ClickHouse 查询语句。
特别注意 ClickHouse 的语法特性：
- 高性能分析型数据库，适合大数据量的聚合查询
- 支持 groupArray, groupUniqArray 等数组聚合函数
- 支持 ANY, ALL 等特殊操作符
- 日期处理函数丰富，如 today(), yesterday()"""
        }

        return system_prompts.get(db_type_lower,
            """你是一个专业的数据库助手，擅长根据用户需求生成高效的查询语句。
请使用标准 SQL 语法生成查询语句。""")

    def build_complete_sql_prompt(
        self,
        user_input: str,
        table_names: List[str],
        other_messages: str,
        database_type: str = "unknown",
        task_id: Optional[int] = None,
        table_metadata: Optional[Dict[str, Any]] = None,
        table_level_info: Optional[Dict[str, Any]] = None,
        field_level_info: Optional[Dict[str, Any]] = None,
        query_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建完整的SQL生成提示词（用于CreateSQLTool）

        Args:
            user_input: 用户输入
            table_names: 相关表名列表
            other_messages: 其他信息
            database_type: 数据库类型
            table_metadata: 表元数据信息（包含DDL和样例数据）
            table_level_info: 表级别信息（描述、场景等）
            field_level_info: 字段级别信息（业务含义、数据格式等）

        Returns:
            str: 完整的SQL生成提示词
        """
        prompt_parts = []

        # 根据数据库类型添加特定的系统提示词
        db_system_prompt = self._get_database_system_prompt(database_type)
        prompt_parts.append(db_system_prompt)

        # 选择表的理由
        prompt_parts.append("选择的表：")
        prompt_parts.append("=" * 50)
        prompt_parts.append(other_messages)

        # 表详细信息
        prompt_parts.append("数据库表详细信息：")
        prompt_parts.append("=" * 50)

        # 如果有详细的表信息，使用它们
        if table_metadata or table_level_info or field_level_info:
            prompt_parts.append(self._build_detailed_table_info(
                table_names, table_metadata, table_level_info, field_level_info, query_context
            ))
        else:
            # 否则使用基本的表信息
            prompt_parts.append(self.build_table_detail_prompt(table_names, task_id=task_id))

        # 表关系信息
        prompt_parts.append("\n" + "=" * 50)
        prompt_parts.append("表的关联关系：")
        prompt_parts.append(self.build_table_relationship_prompt(table_names, task_id))


        # SQL生成规则
        prompt_parts.append("\n" + "=" * 50)
        prompt_parts.append("创建sql的规则：")
        prompt_parts.append(self.build_table_size_join_order_prompt(table_names, task_id=task_id))

        # 用户输入
        prompt_parts.append("\n" + "=" * 50)
        prompt_parts.append(f"用户输入: {user_input}")
        prompt_parts.append("请根据上述数据库表结构和规则，生成对应的SQL查询语句。")
        # ⚠️ 强约束输出格式（这是关键）
        output_requirements = f"""
【输出要求 - 必须严格遵守】
1. 只能按照以下格式返回，不允许有任何多余内容
2. SQL 必须是 {database_type} 数据库可直接执行的 SQL，严格遵循该数据库的语法规范
3. SQL 只能出现一次
4. 理由必须是条目化说明，说明每个关键设计点

【返回格式示例】

【SQL】
SELECT ...
FROM ...
WHERE ...
GROUP BY ...

【理由】
1. 选择 xxx 表是因为 ...
2. 不选择 yyy 表是因为 ...
3. 使用 xxx 字段作为过滤条件是因为 ...
4. 选择了符合 {database_type} 数据库特性的优化方式
5. 选择了关联字段 xxx 和 yyy 进行连接是因为
    """
        prompt_parts.append(output_requirements)
        return "\n".join(prompt_parts)

    def build_table_detail_prompt(self, table_names: List[str], task_id: Optional[int] = None) -> str:
        """
        构建表详细信息提示词

        Args:
            table_names: 表名列表

        Returns:
            str: 表详细信息
        """
        prompt_parts = []

        for table_name in table_names:
            prompt_parts.append(f"\n表: {table_name}")
            prompt_parts.append("-" * 40)

            # 获取表元数据
            metadata_query = self.db.query(TableMetadataBasic).filter(
                TableMetadataBasic.table_name == table_name
            )
            if task_id is not None:
                metadata_query = metadata_query.filter(TableMetadataBasic.table_task_id == task_id)
            metadata = metadata_query.first()

            if metadata:
                # 显示DDL（截取前500字符）
                if metadata.table_ddl:
                    ddl = metadata.table_ddl[:500] + "..." if len(metadata.table_ddl) > 500 else metadata.table_ddl
                    prompt_parts.append(f"DDL: {ddl}")

                # 显示样例数据（最多2条）
                sample_data_list = self.db.query(TableSampleData).filter(
                    TableSampleData.table_metadata_id == metadata.id
                ).limit(1).all()

                if sample_data_list:
                    prompt_parts.append("\n样例数据:")
                    for i, sample in enumerate(sample_data_list, 1):
                        prompt_parts.append(f"  样例{i}: {sample.sample_data}")

            prompt_parts.append("")

        return "\n".join(prompt_parts)

    def build_table_relationship_prompt(self, table_names: List[str] = None, task_id: Optional[int] = None) -> str:
        """
        构建表关系提示词，从数据库中获取真实的表关联关系

        Args:
            table_names: 需要查询关系的表名列表（可选）
            task_id: 任务ID（可选，用于隔离同名表跨任务干扰）

        Returns:
            str: 表关系信息
        """
        if not table_names:
            return "未指定表名，无法获取表关系信息。"

        # 获取表之间的关联关系
        relationships = self._get_table_relationships(table_names, task_id)

        if not relationships:
            return "未找到表之间的关联关系，请根据字段名推断可能的JOIN条件。"

        # 构建关系提示词
        prompt_parts = []
        prompt_parts.append("表之间的关联关系（JOIN 信息）：")
        prompt_parts.append("=" * 50)

        for i, relation in enumerate(relationships, 1):
            source_table = relation['source_table']
            target_table = relation['target_table']
            source_field = relation['source_field']
            target_field = relation['target_field']
            relation_type = relation['relation_type']
            description = relation.get('description', '')

            prompt_parts.append(f"\n{i}. {source_table} -> {target_table}")
            prompt_parts.append(f"   关联字段: {source_table}.{source_field} = {target_table}.{target_field}")
            prompt_parts.append(f"   关联类型: {relation_type}")

            if description:
                prompt_parts.append(f"   说明: {description}")

        # 添加使用建议
        prompt_parts.append(f"\n{'='*50}")
        prompt_parts.append("JOIN 使用建议：")
        prompt_parts.append("1. 使用上述明确的关联字段进行 JOIN")
        prompt_parts.append("2. 注意 JOIN 的顺序，考虑表的大小以提高性能")
        prompt_parts.append("3. 确保关联字段上有适当的索引")

        return "\n".join(prompt_parts)

    def _get_table_relationships(self, table_names: List[str], task_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取指定表名列表之间的关联关系

        Args:
            table_names: 表名列表
            task_id: 任务ID（可选）

        Returns:
            List[Dict]: 关联关系列表
        """
        relationships = []

        # 首先获取这些表对应的 TableLevelPrompt
        table_tasks = {}
        for table_name in table_names:
            query = self.db.query(TableLevelPrompt).filter(
                TableLevelPrompt.table_name == table_name,
                TableLevelPrompt.is_active.is_(True)
            )
            if task_id is not None:
                query = query.filter(TableLevelPrompt.task_id == task_id)
            table_prompt = query.first()
            if table_prompt:
                table_tasks[table_name] = table_prompt.id

        if not table_tasks:
            return relationships

        # 获取项目ID列表
        table_prompt_ids = list(table_tasks.values())

        # 查询表字段关联关系
        relations = self.db.query(TableFieldRelation).filter(
            TableFieldRelation.source_table_level_prompt_id.in_(table_prompt_ids),
            TableFieldRelation.target_table_level_prompt_id.in_(table_prompt_ids)
        )
        if task_id is not None:
            relations = relations.filter(TableFieldRelation.nlsql_task_id == task_id)
        relations = relations.all()

        # 创建 task_id 到表名的映射
        id_to_table = {v: k for k, v in table_tasks.items()}

        # 整理关联关系
        for relation in relations:
            source_table = id_to_table.get(relation.source_table_level_prompt_id)
            target_table = id_to_table.get(relation.target_table_level_prompt_id)

            # 只保留两个表都在请求列表中的关系
            if source_table in table_names and target_table in table_names:
                relationships.append({
                    'source_table': source_table,
                    'target_table': target_table,
                    'source_field': relation.source_field_name,
                    'target_field': relation.target_field_name,
                    'relation_type': relation.relation_type,
                    'description': relation.relation_description
                })

        return relationships

    def _build_detailed_table_info(
        self,
        table_names: List[str],
        table_metadata: Optional[Dict[str, Any]] = None,
        table_level_info: Optional[Dict[str, Any]] = None,
        field_level_info: Optional[Dict[str, Any]] = None,
        query_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建详细的表信息提示词，只显示 query_context 中涉及的字段

        Args:
            table_names: 表名列表
            table_metadata: 表元数据信息
            table_level_info: 表级别信息
            field_level_info: 字段级别信息
            query_context: 查询上下文，包含要使用的字段信息

        Returns:
            str: 详细表信息
        """
        # 从 query_context 中提取所有相关的字段
        relevant_fields = self._extract_relevant_fields(query_context, table_names)
        info_parts = []

        for table_name in table_names:
            info_parts.append(f"\n表: {table_name}")
            info_parts.append("-" * 50)

            # 1. 表级别的描述和场景
            if table_level_info and table_name in table_level_info:
                table_info = table_level_info[table_name]

                if table_info.get("table_description"):
                    info_parts.append(f"\n表描述: {table_info['table_description']}")

                if table_info.get("query_scenarios"):
                    info_parts.append(f"\n查询场景:")
                    scenarios = table_info["query_scenarios"]
                    if isinstance(scenarios, list):
                        for scenario in scenarios[:3]:  # 只显示前3个
                            info_parts.append(f"  • {scenario}")
                    else:
                        info_parts.append(f"  • {scenarios}")

                if table_info.get("aggregation_scenarios"):
                    info_parts.append(f"\n聚合场景:")
                    agg_scenarios = table_info["aggregation_scenarios"]
                    if isinstance(agg_scenarios, list):
                        for agg in agg_scenarios[:3]:  # 只显示前3个
                            info_parts.append(f"  • {agg}")
                    else:
                        info_parts.append(f"  • {agg_scenarios}")

            # 2. 表的DDL和样例数据
            if table_metadata and table_name in table_metadata:
                metadata = table_metadata[table_name]

                # DDL信息（截取前500字符）
                if metadata.get("table_ddl"):
                    ddl = metadata["table_ddl"]
                    ddl = ddl[:500] + "..." if len(ddl) > 500 else ddl
                    info_parts.append(f"\n表结构(DDL):\n{ddl}")

                # 样例数据
                sample_data = metadata.get("sample_data", [])
                if sample_data:
                    info_parts.append(f"\n样例数据:")

                    # 处理样例数据，可能是字符串形式的JSON数组
                    processed_samples = []
                    for sample in sample_data:
                        if isinstance(sample, str):
                            # 尝试解析JSON字符串
                            try:
                                parsed = json.loads(sample)
                                if isinstance(parsed, list):
                                    # 如果是数组，取前两个元素
                                    processed_samples.extend(parsed[:2])
                                else:
                                    # 如果是单个对象
                                    processed_samples.append(parsed)
                            except:
                                # 如果解析失败，直接作为字符串处理
                                processed_samples.append(sample[:200] + "..." if len(sample) > 200 else sample)
                        else:
                            processed_samples.append(sample)

                    # 最多显示2条样例数据
                    for i, sample in enumerate(processed_samples[:2], 1):
                        if isinstance(sample, dict):
                            # 如果是字典，显示所有字段，但对每个字段的值进行长度限制
                            items = []
                            for k, v in sample.items():
                                v_str = str(v)
                                if len(v_str) > 200:
                                    v_str = v_str[:200] + "..."
                                items.append(f"{k}: {v_str}")
                            sample_str = "\n    ".join(items)
                            info_parts.append(f"  样例{i}: \n    {sample_str}")
                        else:
                            # 如果是字符串，直接显示（截取长度）
                            sample_str = str(sample)[:200] + "..." if len(str(sample)) > 200 else str(sample)
                            info_parts.append(f"  样例{i}: {sample_str}")

            # 3. 字段详细信息 - 只显示 query_context 中的字段
            if field_level_info and table_name in field_level_info:
                fields_info = field_level_info[table_name]
                table_relevant_fields = relevant_fields.get(table_name, set())

                # 调试信息（在实际使用中可以移除）
                print(f"表 {table_name} 的相关字段: {table_relevant_fields}")
                print(f"表 {table_name} 的字段信息: {list(fields_info.keys()) if fields_info else 'None'}")

                # 如果有字段信息，即使没有相关字段也至少显示一些基本信息
                if fields_info:
                    if table_relevant_fields:
                        info_parts.append(f"\n相关字段信息:")
                        # 显示相关字段
                        count = 0
                        for field_name in table_relevant_fields:
                            if field_name in fields_info and count < 10:  # 最多显示10个相关字段
                                field_data = fields_info[field_name]
                                count += 1
                                info_parts.append(f"\n  {count}. 字段: {field_name}")

                                if field_data.get("business_meaning"):
                                    info_parts.append(f"     业务含义: {field_data['business_meaning']}")

                                if field_data.get("field_description"):
                                    info_parts.append(f"     字段描述: {field_data['field_description']}")

                                if field_data.get("data_format"):
                                    info_parts.append(f"     数据格式: {field_data['data_format']}")

                                if field_data.get("field_type"):
                                    info_parts.append(f"     字段类型: {field_data['field_type']}")

                                if field_data.get("null_rate") is not None:
                                    info_parts.append(f"     空值率: {field_data['null_rate']}%")

                                if field_data.get("unique_count"):
                                    info_parts.append(f"     唯一值数: {field_data['unique_count']}")

                                if field_data.get("sample_data"):
                                    sample = str(field_data["sample_data"])[:100]
                                    info_parts.append(f"     示例值: {sample}...")

                        # 如果字段太多，只显示前10个
                        if count >= 10 and len(table_relevant_fields) > 10:
                            info_parts.append(f"\n  ... 还有 {len(table_relevant_fields) - 10} 个相关字段未显示")
                            break
                    else:
                        # 如果没有相关字段，显示一些主要的字段
                        info_parts.append(f"\n主要字段信息:")
                        count = 0
                        # 优先显示有业务含义的字段
                        for field_name, field_data in fields_info.items():
                            if count >= 5:  # 最多显示5个主要字段
                                break
                            if field_data.get("business_meaning") or field_data.get("field_description"):
                                count += 1
                                info_parts.append(f"\n  {count}. 字段: {field_name}")

                                if field_data.get("business_meaning"):
                                    info_parts.append(f"     业务含义: {field_data['business_meaning']}")

                                if field_data.get("field_description"):
                                    info_parts.append(f"     字段描述: {field_data['field_description']}")

            info_parts.append("")  # 表之间空一行

        return "\n".join(info_parts)

    def _extract_relevant_fields(self, query_context: Dict[str, Any], table_names: List[str]) -> Dict[str, set]:
        """
        从 query_context 中提取所有相关字段

        Args:
            query_context: 查询上下文
            table_names: 表名列表

        Returns:
            Dict[str, set]: 每个表的相关字段集合
        """
        relevant_fields = {table_name: set() for table_name in table_names}

        if not query_context:
            print("警告: query_context 为空或未定义")
            return relevant_fields

        # 调试信息
        print(f"[调试] query_context 内容: {query_context}")
        print(f"[调试] 需要查找的表: {table_names}")

        # 从 table_usage 中提取字段
        table_usage = query_context.get("table_usage", {})
        print(f"[调试] table_usage: {table_usage}")

        for table_name, usage in table_usage.items():
            if table_name in relevant_fields:
                # 添加各种类型的字段
                if usage.get("filter_fields"):
                    relevant_fields[table_name].update(usage["filter_fields"])
                    # print(f"表 {table_name} 添加过滤字段: {usage['filter_fields']}")

                if usage.get("group_by_fields"):
                    relevant_fields[table_name].update(usage["group_by_fields"])
                    # print(f"表 {table_name} 添加分组字段: {usage['group_by_fields']}")

                if usage.get("agg_fields"):
                    relevant_fields[table_name].update(usage["agg_fields"])
                    # print(f"表 {table_name} 添加聚合字段: {usage['agg_fields']}")

                if usage.get("join_key"):
                    relevant_fields[table_name].add(usage["join_key"])
                    # print(f"表 {table_name} 添加连接字段: {usage['join_key']}")

        # 从 joins 中提取关联字段
        joins = query_context.get("joins", [])
        for join in joins:
            from_table_field = join.get("from", "").split(".")
            to_table_field = join.get("to", "").split(".")

            # 处理 from 字段
            if len(from_table_field) == 2:
                from_table, from_field = from_table_field
                if from_table in relevant_fields:
                    relevant_fields[from_table].add(from_field)

            # 处理 to 字段
            if len(to_table_field) == 2:
                to_table, to_field = to_table_field
                if to_table in relevant_fields:
                    relevant_fields[to_table].add(to_field)

        # 调试输出
        print(f"[调试] 提取到的相关字段: {relevant_fields}")

        return relevant_fields

    def build_table_size_join_order_prompt(self, table_names: List[str], task_id: Optional[int] = None) -> str:
        """
        构建表大小和连接顺序提示词

        Args:
            table_names: 表名列表

        Returns:
            str: 表大小和连接顺序规则
        """
        prompt_parts = []

        # 获取表的大小信息
        table_sizes = {}
        for table_name in table_names:
            metadata_query = self.db.query(TableMetadataBasic).filter(
                TableMetadataBasic.table_name == table_name
            )
            if task_id is not None:
                metadata_query = metadata_query.filter(TableMetadataBasic.table_task_id == task_id)
            metadata = metadata_query.first()
            if metadata and metadata.table_row_count:
                table_sizes[table_name] = metadata.table_row_count
            else:
                table_sizes[table_name] = 0

        # 按大小排序
        sorted_tables = sorted(table_sizes.items(), key=lambda x: x[1] if x[1] else float('inf'))

        prompt_parts.append("\n1. 表大小信息（行数）:")
        for table_name, row_count in sorted_tables[:5]:  # 只显示前5个
            count_str = f"{row_count}" if row_count else "未知"
            prompt_parts.append(f"   {table_name}: {count_str}")

        prompt_parts.append("\n2. JOIN优化规则:")
        prompt_parts.append("   - 优先使用大表作为驱动表")
        prompt_parts.append("   - JOIN顺序：大表 -> 小表")
        prompt_parts.append("   - 确保JOIN字段上有索引")

        prompt_parts.append("\n3. SQL生成规则:")
        prompt_parts.append("   - 只使用已明确提及的字段")
        prompt_parts.append("   - 避免不必要的子查询")
        prompt_parts.append("   - 使用WHERE而不是HAVING进行过滤")
        prompt_parts.append("   -聚合时注意NULL值处理")

        return "\n".join(prompt_parts)

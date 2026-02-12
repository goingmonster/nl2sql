-- 1. 数据库配置表
CREATE TABLE IF NOT EXISTS db_config (
    id BIGSERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL COMMENT '数据库类型 PG CK MYSQL',
    database_name VARCHAR(100) NOT NULL COMMENT '数据库名称',
    schema_name VARCHAR(100) DEFAULT 'public' COMMENT 'schema名称，默认public postgres 其他的数据库没有',
    ip VARCHAR(45) NOT NULL COMMENT 'IP地址',
    port INTEGER NOT NULL COMMENT '端口',
    username VARCHAR(100) NOT NULL COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE db_config IS '数据库配置表';
COMMENT ON COLUMN db_config.id IS '主键';
COMMENT ON COLUMN db_config.type IS '数据库类型 PG CK';
COMMENT ON COLUMN db_config.database_name IS '数据库名称';
COMMENT ON COLUMN db_config.schema_name IS 'public postgres';
COMMENT ON COLUMN db_config.ip IS 'IP地址';
COMMENT ON COLUMN db_config.port IS '端口';
COMMENT ON COLUMN db_config.username IS '用户名';
COMMENT ON COLUMN db_config.password IS '密码';

-- 2. LLM配置表
CREATE TABLE IF NOT EXISTS llm_config (
    id BIGSERIAL PRIMARY KEY,
    base_url VARCHAR(500) NOT NULL COMMENT 'URL地址',
    model_name VARCHAR(500) NOT NULL COMMENT '模型名称',
    api_key VARCHAR(500) NOT NULL COMMENT 'API密钥',
    max_tokens INTEGER DEFAULT 4096 COMMENT '最大token配置',
    temperature DECIMAL(3,2) DEFAULT 0.7 COMMENT '温度参数',
    description TEXT COMMENT '描述',
    provider VARCHAR(100) NOT NULL COMMENT '供应商',
    status INTEGER DEFAULT 1 COMMENT '状态：1-启用，2-禁用',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE llm_config IS 'LLM配置表';
COMMENT ON COLUMN llm_config.id IS '主键';
COMMENT ON COLUMN llm_config.model_name IS '模型名称';
COMMENT ON COLUMN llm_config.base_url IS 'url';
COMMENT ON COLUMN llm_config.api_key IS 'key';
COMMENT ON COLUMN llm_config.max_tokens IS '最大token配置';
COMMENT ON COLUMN llm_config.temperature IS '温度';
COMMENT ON COLUMN llm_config.description IS '描述';
COMMENT ON COLUMN llm_config.provider IS '供应商';
COMMENT ON COLUMN llm_config.status IS '状态（1，2）';

-- 3. NL2SQL任务配置表（核心表）
CREATE TABLE IF NOT EXISTS nlsql_task_config (
    id BIGSERIAL PRIMARY KEY,
    llm_config_id BIGINT NOT NULL REFERENCES llm_config(id) ON DELETE CASCADE,
    db_config_id BIGINT NOT NULL REFERENCES db_config(id) ON DELETE CASCADE,
    user_prompt_config_id BIGINT NOT NULL REFERENCES user_prompt_config(id) ON DELETE CASCADE,
    select_tables JSONB COMMENT '选中的表元数据ID列表，格式为数组如[1,2,3]，用于限制NL2SQL查询的表范围 '
    description TEXT COMMENT '任务描述',
    status INTEGER DEFAULT 1 COMMENT '任务状态：1-初始化，2-提取元数据，3-生成表提示词，4-生成字段提示词，5-完成',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE nlsql_task_config IS 'nl2sql任务配置表';
COMMENT ON COLUMN nlsql_task_config.id IS '主键';
COMMENT ON COLUMN nlsql_task_config.llm_config_id IS 'llm配置外键';
COMMENT ON COLUMN nlsql_task_config.db_config_id IS '数据库配置外键';
COMMENT ON COLUMN nlsql_task_config.user_prompt_config_id IS '提示词生成配置ID';
COMMENT ON COLUMN nlsql_task_config.description IS '任务描述';
COMMENT ON COLUMN nlsql_task_config.status IS '任务状态1，2，3，4，5，6，7';

-- 4. 表元数据
CREATE TABLE IF NOT EXISTS table_metadata (
    id BIGSERIAL PRIMARY KEY,
    db_config_id BIGINT NOT NULL REFERENCES db_config(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL COMMENT '表名称',
    table_description TEXT COMMENT '表描述（人工添加或者自动获取）',
    table_row_count BIGINT COMMENT '表行数',
    table_ddl TEXT COMMENT '创建表语句',
    table_type VARCHAR(50) COMMENT '表类型：枚举 事实 日志',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(db_config_id, table_name)
);

COMMENT ON TABLE table_metadata IS '表元数据';
COMMENT ON COLUMN table_metadata.id IS '主键';
COMMENT ON COLUMN table_metadata.db_config_id IS 'db_config_id外键';
COMMENT ON COLUMN table_metadata.table_name IS '表名称';
COMMENT ON COLUMN table_metadata.table_description IS '表描述（人工添加或者自动获取）';
COMMENT ON COLUMN table_metadata.table_row_count IS '表行数';
COMMENT ON COLUMN table_metadata.table_ddl IS '创建表语句';
COMMENT ON COLUMN table_metadata.table_type IS '表类型：枚举 事实 日志';

-- 5. 表样例数据
CREATE TABLE IF NOT EXISTS table_sample_data (
    id BIGSERIAL PRIMARY KEY,
    table_metadata_id BIGINT NOT NULL REFERENCES table_metadata(id) ON DELETE CASCADE,
    sample_data JSONB NOT NULL COMMENT '样例数据',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE table_sample_data IS '表样例数据';
COMMENT ON COLUMN table_sample_data.id IS '主键';
COMMENT ON COLUMN table_sample_data.table_metadata_id IS '表元数据id外键';
COMMENT ON COLUMN table_sample_data.sample_data IS '样例数据';

-- 6. 表内字段元数据
CREATE TABLE IF NOT EXISTS table_field_metadata (
    id BIGSERIAL PRIMARY KEY,
    table_metadata_id BIGINT NOT NULL REFERENCES table_metadata(id) ON DELETE CASCADE,
    field_name VARCHAR(255) NOT NULL COMMENT '字段名称',
    field_type VARCHAR(100) COMMENT '字段类型',
    null_rate DECIMAL(5,4) COMMENT '空置率',
    field_description TEXT COMMENT '字段描述+注释',
    unique_count BIGINT COMMENT '唯一值数量',
    sample_values JSONB COMMENT '样例值列表',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(table_metadata_id, field_name)
);

COMMENT ON TABLE table_field_metadata IS '表内字段元数据';
COMMENT ON COLUMN table_field_metadata.id IS '主键';
COMMENT ON COLUMN table_field_metadata.table_metadata_id IS '表元数据id外键';
COMMENT ON COLUMN table_field_metadata.field_name IS '字段名称';
COMMENT ON COLUMN table_field_metadata.field_type IS '字段类型';
COMMENT ON COLUMN table_field_metadata.null_rate IS '空置率';
COMMENT ON COLUMN table_field_metadata.field_description IS '字段描述+注释';
COMMENT ON COLUMN table_field_metadata.unique_count IS '唯一值数量';

-- 7. 表级别提示词
CREATE TABLE IF NOT EXISTS table_level_prompt (
    id BIGSERIAL PRIMARY KEY,
    nlsql_task_id BIGINT NOT NULL REFERENCES nlsql_task_config(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL COMMENT '表名称',
    query_scenarios TEXT COMMENT '查询场景',
    aggregation_scenarios TEXT COMMENT '聚合场景',
    data_role VARCHAR(255) COMMENT '表数据角色',
    usage_not_scenarios TEXT COMMENT '不推荐的用法',
    system_description TEXT COMMENT '系统级别的描述',
    table_notes TEXT COMMENT '表的备注',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(nlsql_task_id, table_name)
);

COMMENT ON TABLE table_level_prompt IS '表级别提示词';
COMMENT ON COLUMN table_level_prompt.id IS '主键';
COMMENT ON COLUMN table_level_prompt.nlsql_task_id IS 'nlsql的任务id外键';
COMMENT ON COLUMN table_level_prompt.table_name IS '表名称';
COMMENT ON COLUMN table_level_prompt.query_scenarios IS '查询场景';
COMMENT ON COLUMN table_level_prompt.aggregation_scenarios IS '聚合场景';
COMMENT ON COLUMN table_level_prompt.data_role IS '表数据角色';
COMMENT ON COLUMN table_level_prompt.usage_not_scenarios IS '不推荐的用法';
COMMENT ON COLUMN table_level_prompt.system_description IS '系统级别的描述';
COMMENT ON COLUMN table_level_prompt.table_notes IS '表的备注';

-- 8. 用户提示词配置
CREATE TABLE IF NOT EXISTS user_prompt_config (
    id BIGSERIAL PRIMARY KEY,
    config_name VARCHAR(255) NOT NULL COMMENT '配置名称',
    system_config TEXT COMMENT '系统级别的描述',
    table_notes JSONB COMMENT '表级别的描述（列表）',
    field_notes JSONB COMMENT '字段级别的描述（列表）',
    config_type INTEGER COMMENT '配置类型：1-默认，2-自定义，3-系统预制',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE user_prompt_config IS '用户提示词配置表';
COMMENT ON COLUMN user_prompt_config.id IS '主键';
COMMENT ON COLUMN user_prompt_config.config_name IS '配置名称';
COMMENT ON COLUMN user_prompt_config.system_config IS '系统级别的描述';
COMMENT ON COLUMN user_prompt_config.table_notes IS '表级别的描述（列表）';
COMMENT ON COLUMN user_prompt_config.field_notes IS '字段级别的描述（列表）';
COMMENT ON COLUMN user_prompt_config.config_type IS '（1，2，3）如果没有就使用默认的配置';

-- 9. 表字段关联关系
CREATE TABLE IF NOT EXISTS table_field_relation (
    id BIGSERIAL PRIMARY KEY,
    nlsql_task_id BIGINT NOT NULL REFERENCES nlsql_task_config(id) ON DELETE CASCADE,
    source_table_field_prompt_id BIGINT COMMENT '关联源字段提示词id',
    source_table_level_prompt_id BIGINT COMMENT '关联源表提示词id',
    target_table_field_prompt_id BIGINT COMMENT '关联目标字段提示词id',
    target_table_level_prompt_id BIGINT COMMENT '关联目标表提示词id',
    relation_type VARCHAR(100) NOT NULL COMMENT '关联类型',
    relation_description TEXT COMMENT '关联描述',
    confidence DECIMAL(3,2) COMMENT '置信度',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE table_field_relation IS '表字段关联关系';
COMMENT ON COLUMN table_field_relation.id IS '主键';
COMMENT ON COLUMN table_field_relation.nlsql_task_id IS 'nlsql的任务id外键';
COMMENT ON COLUMN table_field_relation.source_table_field_prompt_id IS '关联源字段提示词id';
COMMENT ON COLUMN table_field_relation.source_table_level_prompt_id IS '关联源表提示词id';
COMMENT ON COLUMN table_field_relation.target_table_field_prompt_id IS '关联目标字段提示词id';
COMMENT ON COLUMN table_field_relation.target_table_level_prompt_id IS '关联目标表提示词id';
COMMENT ON COLUMN table_field_relation.relation_type IS '关联类型';
COMMENT ON COLUMN table_field_relation.relation_description IS '关联描述';
COMMENT ON COLUMN table_field_relation.confidence IS '置信度';

-- 10. 表字段提示词
CREATE TABLE IF NOT EXISTS table_field_prompt (
    id BIGSERIAL PRIMARY KEY,
    nlsql_task_id BIGINT NOT NULL REFERENCES nlsql_task_config(id) ON DELETE CASCADE,
    table_level_prompt_id BIGINT REFERENCES table_level_prompt(id) ON DELETE CASCADE,
    field_name VARCHAR(255) NOT NULL COMMENT '字段名称',
    business_meaning TEXT COMMENT '业务含义',
    data_format VARCHAR(500) COMMENT '数据样式',
    field_description TEXT COMMENT '字段描述',
    query_scenarios TEXT COMMENT '查询场景',
    aggregation_scenarios TEXT COMMENT '聚合场景',
    rules TEXT COMMENT '使用规则',
    database_usage TEXT COMMENT '数据库使用方式',
    field_type VARCHAR(100) COMMENT '字段类型',
    null_rate DECIMAL(5,4) COMMENT '空置率',
    unique_count BIGINT COMMENT '唯一值数量',
    sample_values JSONB COMMENT '样例数据',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE table_field_prompt IS '表字段提示词';
COMMENT ON COLUMN table_field_prompt.id IS '主键';
COMMENT ON COLUMN table_field_prompt.nlsql_task_id IS 'nlsql的任务id外键';
COMMENT ON COLUMN table_field_prompt.table_level_prompt_id IS '表描述关联id外键';
COMMENT ON COLUMN table_field_prompt.field_name IS '字段名称';
COMMENT ON COLUMN table_field_prompt.business_meaning IS '业务含义';
COMMENT ON COLUMN table_field_prompt.data_format IS '数据样式';
COMMENT ON COLUMN table_field_prompt.field_description IS '字段描述';
COMMENT ON COLUMN table_field_prompt.query_scenarios IS '查询场景';
COMMENT ON COLUMN table_field_prompt.aggregation_scenarios IS '聚合场景';
COMMENT ON COLUMN table_field_prompt.rules IS '使用规则';
COMMENT ON COLUMN table_field_prompt.database_usage IS '数据库使用方式';
COMMENT ON COLUMN table_field_prompt.field_type IS '字段类型';
COMMENT ON COLUMN table_field_prompt.null_rate IS '空置率';
COMMENT ON COLUMN table_field_prompt.unique_count IS '唯一值数量';
COMMENT ON COLUMN table_field_prompt.sample_values IS '样例数据';

-- 11. 用户问答对
CREATE TABLE IF NOT EXISTS qa_embedding (
    id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL COMMENT '问题',
    nlsql_task_id BIGINT NOT NULL REFERENCES nlsql_task_config(id) ON DELETE CASCADE,
    sql TEXT NOT NULL COMMENT 'SQL',
    where_conditions JSONB COMMENT 'WHERE条件',
    tables JSONB COMMENT '使用的表',
    is_enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE qa_embedding IS '用户问答对';
COMMENT ON COLUMN qa_embedding.id IS '主键';
COMMENT ON COLUMN qa_embedding.question IS '问题';
COMMENT ON COLUMN qa_embedding.nlsql_task_id IS 'nlsql任务id外键';
COMMENT ON COLUMN qa_embedding.sql IS 'SQL';
COMMENT ON COLUMN qa_embedding.where_conditions IS 'WHERE条件';
COMMENT ON COLUMN qa_embedding.tables IS '使用的表';
COMMENT ON COLUMN qa_embedding.is_enabled IS '是否启用';

-- 12. 用户知识库
CREATE TABLE IF NOT EXISTS knowledges (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL COMMENT '知识内容',
    is_open BOOLEAN DEFAULT TRUE COMMENT '是否公开',
    nlsql_task_id BIGINT NOT NULL REFERENCES nlsql_task_config(id) ON DELETE CASCADE,
    conversation_id BIGINT REFERENCES conversation(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE knowledges IS '用户知识库';
COMMENT ON COLUMN knowledges.id IS '主键';
COMMENT ON COLUMN knowledges.content IS '内容';
COMMENT ON COLUMN knowledges.is_open IS '是否公开';
COMMENT ON COLUMN knowledges.nlsql_task_id IS 'nlsql任务id外键';
COMMENT ON COLUMN knowledges.conversation_id IS '对话id外键';

-- 13. 会话表
CREATE TABLE IF NOT EXISTS chat_session (
    id BIGSERIAL PRIMARY KEY,
    nlsql_task_id BIGINT NOT NULL REFERENCES nlsql_task_config(id) ON DELETE CASCADE,
    session_title VARCHAR(255) COMMENT '会话标题',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE chat_session IS '会话表';
COMMENT ON COLUMN chat_session.id IS '主键';
COMMENT ON COLUMN chat_session.nlsql_task_id IS 'nlsql任务id外键';
COMMENT ON COLUMN chat_session.session_title IS '会话标题';

-- 14. 聊天记录
CREATE TABLE IF NOT EXISTS conversation (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES chat_session(id) ON DELETE CASCADE,
    question TEXT NOT NULL COMMENT '问题',
    answer TEXT COMMENT '回答',
    description TEXT COMMENT '描述',
    nlsql_task_id BIGINT NOT NULL REFERENCES nlsql_task_config(id) ON DELETE CASCADE,
    is_right BOOLEAN COMMENT '是否正确',
    sql_generated TEXT COMMENT '生成的SQL',
    sql_result TEXT COMMENT 'SQL执行返回数据(JSON)',
    selected_tables TEXT COMMENT '选表代理返回的表列表(JSON)',
    query_context TEXT COMMENT '查询上下文(JSON)',
    column_patch TEXT COMMENT '列补丁(JSON)',
    feedback TEXT COMMENT '反馈信息',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE conversation IS '聊天记录';
COMMENT ON COLUMN conversation.id IS '主键';
COMMENT ON COLUMN conversation.session_id IS '所属会话id外键';
COMMENT ON COLUMN conversation.question IS '问题';
COMMENT ON COLUMN conversation.answer IS '回答';
COMMENT ON COLUMN conversation.description IS '描述';
COMMENT ON COLUMN conversation.nlsql_task_id IS 'nlsql任务id外键';
COMMENT ON COLUMN conversation.is_right IS '是否正确';
COMMENT ON COLUMN conversation.sql_generated IS '生成的SQL';
COMMENT ON COLUMN conversation.sql_result IS 'SQL执行返回数据(JSON)';
COMMENT ON COLUMN conversation.selected_tables IS '选表代理返回的表列表(JSON)';
COMMENT ON COLUMN conversation.query_context IS '查询上下文(JSON)';
COMMENT ON COLUMN conversation.column_patch IS '列补丁(JSON)';
COMMENT ON COLUMN conversation.feedback IS '反馈信息';

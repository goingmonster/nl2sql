-- SQLite版本的建表语句

-- 1. 数据库配置表
CREATE TABLE IF NOT EXISTS db_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    database_name TEXT NOT NULL,
    schema_name TEXT DEFAULT 'public',
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
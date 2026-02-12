from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # 忽略额外的环境变量
    )

    PROJECT_NAME: str = "NL2SQL API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Worker 配置
    WORKERS: int = 2  # 默认 2 个进程
    PORT: int = 8000  # 默认端口

    # CORS - 允许前端开发服务器
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "*"  # 开发环境允许所有来源
    ]

    # SQLite Database
    SQLITE_URL: str = "sqlite:///./app.db"


settings = Settings()
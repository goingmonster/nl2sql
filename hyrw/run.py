import uvicorn
import os

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式使用reload
        workers=1,  # 开发模式使用单进程，避免reload和多进程冲突
    )
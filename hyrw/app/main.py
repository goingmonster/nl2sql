from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.api.v1.router import api_router
from app.core.database import init_db
from app.models import *  # 导入所有模型
from app.core.exceptions import NotFoundError, ValidationError, BaseAPIError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="NL2SQL API",
    lifespan=lifespan
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Exception handlers
@app.exception_handler(NotFoundError)
async def not_found_exception_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.message,
            "data": None
        }
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.message,
            "data": exc.details
        }
    )


@app.exception_handler(BaseAPIError)
async def base_api_exception_handler(request: Request, exc: BaseAPIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.message,
            "data": exc.details
        }
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    import json
    from pydantic_core import PydanticUndefined

    def serialize_value(value):
        if value is PydanticUndefined:
            return None
        return value

    # 序列化错误详情，处理PydanticUndefined
    serialized_errors = []
    for error in exc.errors():
        serialized_error = {}
        for key, val in error.items():
            serialized_error[key] = serialize_value(val)
        serialized_errors.append(serialized_error)

    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "请求参数验证失败",
            "data": serialized_errors
        }
    )


@app.get("/")
async def root():
    return {"message": "NL2SQL API is running", "version": settings.VERSION}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
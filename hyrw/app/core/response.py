from typing import Any, Optional, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T')


class BaseResponse(BaseModel, Generic[T]):
    """基础响应模型"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class SuccessResponse(BaseResponse[T]):
    """成功响应"""
    def __init__(self, data: T = None, message: str = "success", **kwargs):
        super().__init__(code=200, message=message, data=data, **kwargs)


class ErrorResponse(BaseResponse):
    """错误响应"""
    def __init__(self, code: int = 400, message: str = "error", data: Any = None, **kwargs):
        super().__init__(code=code, message=message, data=data, **kwargs)


class PaginationMeta(BaseModel):
    """分页元信息"""
    page: int
    page_size: int
    total: int
    pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    items: list[T]
    meta: PaginationMeta

    def __init__(self, items: list[T] = None, total: int = 0, page: int = 1, page_size: int = 20, **kwargs):
        pages = (total + page_size - 1) // page_size
        meta = PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            pages=pages
        )
        super().__init__(items=items or [], meta=meta, **kwargs)


def success_response(data: Any = None, message: str = "success") -> SuccessResponse:
    """创建成功响应"""
    return SuccessResponse(data=data, message=message)


def error_response(code: int = 400, message: str = "error", data: Any = None) -> ErrorResponse:
    """创建错误响应"""
    return ErrorResponse(code=code, message=message, data=data)
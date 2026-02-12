from typing import Generic, TypeVar, Any, Dict
from pydantic import BaseModel

T = TypeVar('T')


class PaginationInfo(BaseModel):
    """分页信息"""
    page: int
    page_size: int
    total: int
    pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    code: int = 200
    message: str = "success"
    data: T
    pagination: PaginationInfo
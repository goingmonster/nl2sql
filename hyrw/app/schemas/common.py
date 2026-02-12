from typing import Any, Optional, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """统一的API响应模型"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None
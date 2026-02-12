from typing import Any


class BaseAPIError(Exception):
    """基础API异常类"""

    def __init__(self, message: str, status_code: int = 400, details: Any = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class NotFoundError(BaseAPIError):
    """资源未找到异常"""

    def __init__(self, message: str = "资源未找到"):
        super().__init__(message=message, status_code=404)


class ValidationError(BaseAPIError):
    """验证错误异常"""

    def __init__(self, message: str = "验证失败", details: Any = None):
        super().__init__(message=message, status_code=422, details=details)


class ConflictError(BaseAPIError):
    """冲突异常"""

    def __init__(self, message: str = "资源冲突"):
        super().__init__(message=message, status_code=409)


class UnauthorizedError(BaseAPIError):
    """未授权异常"""

    def __init__(self, message: str = "未授权访问"):
        super().__init__(message=message, status_code=401)


class ForbiddenError(BaseAPIError):
    """禁止访问异常"""

    def __init__(self, message: str = "禁止访问"):
        super().__init__(message=message, status_code=403)


class InternalServerError(BaseAPIError):
    """内部服务器错误"""

    def __init__(self, message: str = "内部服务器错误"):
        super().__init__(message=message, status_code=500)
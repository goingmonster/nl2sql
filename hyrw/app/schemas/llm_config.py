from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class LlmConfigBase(BaseModel):
    base_url: str = Field(..., description="URL地址", max_length=500)
    api_key: str = Field(..., description="API密钥", max_length=500)
    max_tokens: Optional[int] = Field(4096, description="最大token配置", ge=1)
    temperature: Optional[float] = Field(0.7, description="温度参数", ge=0.0, le=2.0)
    description: Optional[str] = Field(None, description="描述")
    provider: str = Field(..., description="供应商", max_length=100)
    model_name: str = Field(..., description="模型名称", max_length=100)
    status: Optional[int] = Field(1, description="状态：1-启用，2-禁用", ge=1, le=2)


class LlmConfigCreate(LlmConfigBase):
    pass


class LlmConfigUpdate(BaseModel):
    base_url: Optional[str] = Field(None, description="URL地址", max_length=500)
    api_key: Optional[str] = Field(None, description="API密钥", max_length=500)
    max_tokens: Optional[int] = Field(None, description="最大token配置", ge=1)
    temperature: Optional[float] = Field(None, description="温度参数", ge=0.0, le=2.0)
    description: Optional[str] = Field(None, description="描述")
    provider: Optional[str] = Field(None, description="供应商", max_length=100)
    model_name: Optional[str] = Field(None, description="模型名称", max_length=100)
    status: Optional[int] = Field(None, description="状态：1-启用，2-禁用", ge=1, le=2)


class LlmConfigResponse(LlmConfigBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LlmConfigQuery(BaseModel):
    provider: Optional[str] = Field(None, description="供应商")
    model_name: Optional[str] = Field(None, description="模型名称")
    status: Optional[int] = Field(None, description="状态：1-启用，2-禁用")
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(20, description="每页数量", ge=1, le=100)
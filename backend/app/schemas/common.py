"""
SmartCart AI - Common Response & Error Schemas
"""

from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", json_schema_extra={"example": "ok"})
    app_name: str
    environment: str
    database_status: str = Field(json_schema_extra={"example": "connected"})
    timestamp: datetime


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Any] = None

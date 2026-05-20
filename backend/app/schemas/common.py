from __future__ import annotations
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int


class WarningResponse(BaseModel):
    warnings: List[str] = []

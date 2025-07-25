from pydantic import BaseModel, Field
from typing import Generic, TypeVar

T = TypeVar("T")


class Pager(BaseModel, Generic[T]):
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Number of items per page")
    total: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")
    items: list[T] = Field(description="List of items for the current page")


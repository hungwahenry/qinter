"""
registry-backend/app/schemas/search.py
"""

from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class SortOrder(str, Enum):
    """Sort order options."""
    RELEVANCE = "relevance"
    DOWNLOADS = "downloads"
    RATING = "rating"
    NAME = "name"
    UPDATED = "updated"
    CREATED = "created"


class SearchQuery(BaseModel):
    """Search query parameters."""
    q: str
    limit: int = 20
    offset: int = 0
    sort: SortOrder = SortOrder.RELEVANCE
    tags: Optional[List[str]] = None
    targets: Optional[List[str]] = None  # Exception types
    author: Optional[str] = None
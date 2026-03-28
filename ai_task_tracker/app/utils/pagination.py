"""Pagination utility helpers."""
import math
from typing import Any, Dict, List, Type, TypeVar

from pydantic import BaseModel

from app.schemas.common import PaginatedResponse, PaginationMeta

T = TypeVar("T", bound=BaseModel)


def paginate(
    items: List[Any],
    total: int,
    page: int,
    per_page: int,
) -> Dict:
    """Build a standardised paginated response dict."""
    total_pages = max(1, math.ceil(total / per_page))
    return {
        "success": True,
        "data": items,
        "meta": PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    }


def get_skip(page: int, per_page: int) -> int:
    return (page - 1) * per_page

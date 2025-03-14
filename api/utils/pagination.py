from typing import TypeVar, Any
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel):
    """
    Generic model for paginated responses.
    """
    items: list[Any]
    total: int
    total_public: int
    total_anonymous: int
    page: int
    size: int
    pages: int
    has_more: bool
    is_public_current_user: bool
    current_user: dict[str, bool]
    
    class Config:
        arbitrary_types_allowed = True




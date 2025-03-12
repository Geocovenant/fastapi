from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import List

from api.database import get_session
from api.public.tag.models import TagRead
from api.public.tag.crud import get_all_tags

router = APIRouter()

@router.get("/", response_model=List[TagRead])
async def read_tags(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    session: Session = Depends(get_session)
):
    """
    Retrieves a paginated list of all tags
    """
    tags = get_all_tags(session=session, skip=skip, limit=limit)
    return tags 
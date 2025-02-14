from fastapi import APIRouter, Depends
from sqlmodel import Session
from api.public.community.models import CommunityRead
from api.public.community.crud import get_community
from api.database import get_session

router = APIRouter()

@router.get("/{community_id}", response_model=CommunityRead)
def read(community_id: int, db: Session = Depends(get_session)):
    return get_community(community_id, db)
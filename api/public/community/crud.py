from fastapi import HTTPException, status
from sqlmodel import Session
from api.public.community.models import Community

def get_community(community_id: int, db: Session) -> Community:
    community = db.get(Community, community_id)
    if not community:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    return community
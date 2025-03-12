from fastapi import HTTPException, status
from sqlmodel import Session, select
from typing import Optional
from api.public.community.models import Community
from api.public.user.models import UserCommunityLink
from api.public.user.models import User
from api.public.community.models import CommunityRequest
from datetime import datetime

def get_community(community_id: int, db: Session, check_membership: bool = False, current_user: Optional[User] = None):
    """
    Get a community by its ID.
    
    Args:
        community_id: ID of the community to retrieve
        db: Database session
        check_membership: If True, checks that the current user is a member
        current_user: Current user (optional)
        
    Returns:
        The community if it exists and the user has access, None otherwise
    """
    community = db.get(Community, community_id)
    
    if not community:
        return None
        
    # Only check membership if explicitly requested
    if check_membership and current_user:
        # Check if the user is a member of the community
        is_member = db.exec(
            select(UserCommunityLink).where(
                UserCommunityLink.user_id == current_user.id,
                UserCommunityLink.community_id == community_id
            )
        ).first() is not None
        
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You are not a member of this community"
            )
    
    return community

def get_community_by_id(session: Session, community_id: int) -> Optional[Community]:
    """
    Get a community by its ID
    
    Args:
        session: Database session
        community_id: ID of the community to search for
        
    Returns:
        Community object if found, None otherwise
    """
    return session.get(Community, community_id)

def get_communities(session: Session, parent_id: Optional[int] = None, 
                   level: Optional[str] = None, skip: int = 0, 
                   limit: int = 100) -> list[Community]:
    """
    Get a list of communities, optionally filtered by parent community or level
    
    Args:
        session: Database session
        parent_id: Optional ID of the parent community to filter
        level: Optional community level to filter
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Community objects
    """
    query = select(Community)
    
    if parent_id is not None:
        query = query.where(Community.parent_id == parent_id)
    
    if level:
        query = query.where(Community.level == level)
    
    return session.exec(query.offset(skip).limit(limit)).all()

def create_community(session: Session, community_data: dict) -> Community:
    """
    Create a new community
    
    Args:
        session: Database session
        community_data: Dictionary with community data
        
    Returns:
        Created Community object
    """
    community = Community(**community_data)
    session.add(community)
    session.commit()
    session.refresh(community)
    return community

def update_community(session: Session, community_id: int, 
                    community_data: dict) -> Optional[Community]:
    """
    Update an existing community
    
    Args:
        session: Database session
        community_id: ID of the community to update
        community_data: Dictionary with data to update
        
    Returns:
        Updated Community object, None if not found
    """
    community = get_community_by_id(session, community_id)
    if not community:
        return None
        
    for key, value in community_data.items():
        setattr(community, key, value)
        
    session.commit()
    session.refresh(community)
    return community

def delete_community(session: Session, community_id: int) -> bool:
    """
    Delete a community
    
    Args:
        session: Database session
        community_id: ID of the community to delete
        
    Returns:
        True if deleted successfully, False if not found
    """
    community = get_community_by_id(session, community_id)
    if not community:
        return False
        
    session.delete(community)
    session.commit()
    return True

def create_community_request(db: Session, request_data: dict):
    """
    Create a new community request in the database
    """
    community_request = CommunityRequest(
        country=request_data["country"],
        region=request_data["region"],
        city=request_data["city"],
        email=request_data["email"]
    )
    db.add(community_request)
    db.commit()
    db.refresh(community_request)
    return community_request

def get_community_requests(db: Session, skip: int = 0, limit: int = 100, status: str = None):
    """
    Get all community requests with optional filtering by status
    """
    query = db.query(CommunityRequest)
    if status:
        query = query.filter(CommunityRequest.status == status)
    return query.offset(skip).limit(limit).all()

def update_community_request_status(db: Session, request_id: int, status: str):
    """
    Update the status of a community request
    """
    community_request = db.query(CommunityRequest).filter(CommunityRequest.id == request_id).first()
    if community_request:
        community_request.status = status
        community_request.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(community_request)
    return community_request
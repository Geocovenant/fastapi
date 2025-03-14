from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from api.database import get_session
from sqlmodel import Session, select, func
from sqlalchemy import distinct
from api.public.user.models import User
from api.public.poll.crud import get_all_polls, create_poll, create_vote, create_or_update_reaction, get_country_polls, get_regional_polls, enrich_poll
from api.public.poll.models import (
    PollCreate, 
    PollRead, 
    PollVoteCreate,
    Poll,
    PollStatus, 
    PollType, 
    PollOption,
    PollVote,
    PollReactionCreate,
    PollComment,
    PollCommentCreate,
    PollCommentUpdate,
    PollCommunityLink,
)
from api.auth.dependencies import get_current_user, get_current_user_optional
from datetime import datetime
from api.public.country.models import Country
from api.public.subregion.models import Subregion
from api.public.community.models import Community
from api.public.region.models import Region
from typing import Optional
from api.utils.generic_models import UserCommunityLink

router = APIRouter()

@router.get("/")
def read_polls(
    scope: str | None = None,
    country: str | None = None,
    region: int | None = None,
    subregion: int | None = None,
    community_id: int | None = None,
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Get polls with optional filters and pagination.
    - scope: Filter by scope (e.g., 'NATIONAL', 'INTERNATIONAL', 'REGIONAL', 'SUBREGIONAL', etc.)
    - country: Filter by country code (CCA2)
    - region: Filter by region ID
    - subregion: Filter by subregion ID
    - community_id: Filter by community ID
    - page: Page number (default: 1)
    - size: Items per page (default: 10, max: 100)
    """
    # Filtrar parámetros indefinidos
    if country == "undefined" or country == "null":
        country = None
    
    if community_id == "undefined" or community_id == "null" or community_id == 0:
        community_id = None
        
    if region == "undefined" or region == "null" or region == 0:
        region = None
        
    if subregion == "undefined" or subregion == "null" or subregion == 0:
        subregion = None
    
    # If a community_id is provided, filter by that community
    if community_id:
        # Check that the community exists
        community = db.exec(
            select(Community)
            .where(Community.id == community_id)
        ).first()
        
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Community with ID {community_id} not found"
            )
        
        # Calculate offset for pagination
        offset = (page - 1) * size
        
        # Base query that joins Poll with PollCommunityLink
        query = (
            select(Poll)
            .join(PollCommunityLink)
            .where(PollCommunityLink.community_id == community_id)
        )
        
        # Apply additional filter by scope if provided
        if scope:
            query = query.where(Poll.scope == scope)
            
        # Another option for the query
        total_query = select(func.count()).select_from(
            select(Poll.id)
            .join(PollCommunityLink)
            .where(PollCommunityLink.community_id == community_id)
            .distinct()
            .subquery()
        )
        total = db.exec(total_query).first() or 0
        total_pages = (total + size - 1) // size if total > 0 else 1
        
        # Apply sorting and pagination
        query = query.order_by(Poll.created_at.desc()).offset(offset).limit(size)
        
        # Execute the query
        polls = db.exec(query).all()
        
        # Enrich with additional information
        return {
            "items": [
                enrich_poll(db, poll, current_user.id if current_user else None)
                for poll in polls
            ],
            "total": total,
            "page": page,
            "size": size,
            "pages": total_pages
        }
    
    # If there is a subregion parameter and the scope is SUBREGIONAL
    if subregion and scope == 'SUBREGIONAL':
        # Verify that the subregion exists
        subregion_obj = db.exec(
            select(Subregion)
            .where(Subregion.id == subregion)
        ).first()

        if not subregion_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subregion with ID {subregion} not found"
            )

        # First, get the community associated with the subregion
        community_id = subregion_obj.community_id
        
        # Now filter the polls that are associated with this community and have the scope SUBREGIONAL
        query = (
            select(Poll)
            .join(PollCommunityLink)
            .where(
                Poll.scope == scope,
                PollCommunityLink.community_id == community_id
            )
        )
        
        # Apply pagination
        total = db.scalar(select(func.count()).select_from(query.subquery()))
        
        # Execute the query
        polls = db.exec(query).all()
        
        # Enrich the polls if there is an authenticated user
        if current_user:
            polls = [
                enrich_poll(db, poll, current_user.id)
                for poll in polls
            ]
            
        return {
            "items": polls,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
    
    # Rest of the original code
    if country:
        return get_country_polls(
            db,
            country_code=country,
            scope=scope,
            current_user_id=current_user.id if current_user else None,
            page=page,
            size=size
        )
    
    if region:
        # Verify that the region exists
        region_obj = db.exec(
            select(Region)
            .where(Region.id == region)
        ).first()

        if not region_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Region with ID {region} not found"
            )

        return get_regional_polls(
            db,
            region_id=region,
            scope=scope,
            current_user_id=current_user.id if current_user else None,
            page=page,
            size=size
        )
    
    return get_all_polls(
        db, 
        scope=scope, 
        current_user_id=current_user.id if current_user else None,
        page=page,
        size=size
    )

@router.post("/", response_model=PollRead, status_code=status.HTTP_201_CREATED)
def create_new_poll(
    poll_data: PollCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a new poll.
    Requires authentication.
    """
    if len(poll_data.options) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The poll must have at least 2 options"
        )
    
    return create_poll(db, poll_data, current_user.id)

@router.post("/{poll_id}/vote", response_model=PollRead)
def vote_poll(
    poll_id: int,
    vote_data: PollVoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Vote on a poll.
    Authentication and membership in the poll's community are required.
    """
    # Verify that the poll exists
    poll = db.get(Poll, poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )
    
    # Verify that the poll is not closed
    if poll.status == PollStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot vote on a closed poll"
        )
    
    # Verify that the user is a member of at least one of the poll's communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    
    user_community_ids = set(user_communities)
    
    poll_communities = db.exec(
        select(PollCommunityLink.community_id)
        .where(PollCommunityLink.poll_id == poll_id)
    ).all()
    
    poll_community_ids = set(poll_communities)
    
    if not user_community_ids.intersection(poll_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to vote in this poll"
        )
    
    # Validate the poll's status
    if poll.status != PollStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot vote in this poll because its status is {poll.status}"
        )
    
    # Validate if the poll has expired
    if poll.ends_at and poll.ends_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This poll expired on {poll.ends_at}"
        )

    # If option_ids is empty, just remove the existing votes
    if len(vote_data.option_ids) == 0:
        # Find and delete existing votes
        existing_votes = db.query(PollVote).filter(
            PollVote.poll_id == poll_id,
            PollVote.user_id == current_user.id
        ).all()
        
        # Decrement vote counters and delete the votes
        for vote in existing_votes:
            option = db.get(PollOption, vote.option_id)
            if option:
                option.votes = max(0, option.votes - 1)
            db.delete(vote)
        
        db.commit()
        db.refresh(poll)
        return poll

    # If there are option_ids, continue with the normal validation...
    valid_options = []
    for option_id in vote_data.option_ids:
        option = db.query(PollOption).filter(
            PollOption.id == option_id,
            PollOption.poll_id == poll_id
        ).first()
        if not option:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Option {option_id} does not exist in poll {poll_id}"
            )
        valid_options.append(option)

    # Validate the number of options according to the poll type
    if poll.type == PollType.BINARY or poll.type == PollType.SINGLE_CHOICE:
        if len(vote_data.option_ids) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This type of poll only allows selecting one option"
            )

    return create_vote(db, poll_id, vote_data.option_ids, current_user.id)

@router.post("/{poll_id}/react", response_model=PollRead)
def react_to_poll(
    poll_id: int,
    reaction_data: PollReactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    React to a poll with like or dislike.
    Authentication required.
    """
    # Verify that the poll exists
    poll = db.get(Poll, poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )
    
    # Verify that the user is a member of at least one of the poll's communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    
    user_community_ids = set(user_communities)
    
    poll_communities = db.exec(
        select(PollCommunityLink.community_id)
        .where(PollCommunityLink.poll_id == poll_id)
    ).all()
    
    poll_community_ids = set(poll_communities)
    
    if not user_community_ids.intersection(poll_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to react to this poll"
        )
    
    return create_or_update_reaction(
        db, 
        poll_id, 
        current_user.id, 
        reaction_data.reaction
    )

@router.get("/{poll_id}/comments")
def get_poll_comments(
    poll_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Get all comments for a specific poll.
    Does not require authentication.
    """
    poll = db.get(Poll, poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    comments = db.exec(
        select(PollComment, User)
        .join(User)
        .where(PollComment.poll_id == poll_id)
        .order_by(PollComment.created_at.desc())
    ).all()

    return [
        {
            **comment.dict(),
            "username": user.username,
            "can_edit": current_user and current_user.id == comment.user_id
        }
        for comment, user in comments
    ]

@router.post("/{poll_id}/comments", status_code=status.HTTP_201_CREATED)
def create_poll_comment(
    poll_id: int,
    comment_data: PollCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a comment on a poll.
    Authentication and membership in the poll's community are required.
    """
    # Verify that the poll exists
    poll = db.get(Poll, poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )
    
    # Verify that the user is a member of at least one of the poll's communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    
    # Usar directamente los enteros
    user_community_ids = set(user_communities)
    
    poll_communities = db.exec(
        select(PollCommunityLink.community_id)
        .where(PollCommunityLink.poll_id == poll_id)
    ).all()
    
    # Usar directamente los enteros
    poll_community_ids = set(poll_communities)
    
    if not user_community_ids.intersection(poll_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to comment on this poll"
        )

    new_comment = PollComment(
        poll_id=poll_id,
        user_id=current_user.id,
        content=comment_data.content,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return {
        **new_comment.dict(),
        "username": current_user.username,
        "can_edit": True
    }

@router.put("/{poll_id}/comments/{comment_id}")
def update_poll_comment(
    poll_id: int,
    comment_id: int,
    comment_data: PollCommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update an existing comment.
    Only the author can edit their comment.
    """
    comment = db.get(PollComment, comment_id)
    if not comment or comment.poll_id != poll_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this comment"
        )

    comment.content = comment_data.content
    comment.updated_at = datetime.utcnow()
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        **comment.dict(),
        "username": current_user.username,
        "can_edit": True
    }

@router.delete("/{poll_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_poll_comment(
    poll_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete a comment.
    Only the author can delete their comment.
    """
    comment = db.get(PollComment, comment_id)
    if not comment or comment.poll_id != poll_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this comment"
        )

    db.delete(comment)
    db.commit()

@router.get("/{poll_id_or_slug}")
def read_poll(
    poll_id_or_slug: str,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Get a specific poll by ID or slug.
    Does not require authentication.
    """
    # Determine if it is an ID or a slug
    if poll_id_or_slug.isdigit():
        poll = db.get(Poll, int(poll_id_or_slug))
    else:
        poll = db.exec(select(Poll).where(Poll.slug == poll_id_or_slug)).first()
    
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )
    
    # Increment view count
    poll.views_count += 1
    db.add(poll)
    db.commit()
    
    # Enrich the poll with additional information
    return enrich_poll(db, poll, current_user.id if current_user else None)

@router.delete("/{poll_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_poll(
    poll_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete a poll.
    Only the creator of the poll can delete it.
    Requires authentication.
    """
    # Verify that the poll exists
    poll = db.get(Poll, poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )
    
    # Verify that the current user is the creator of the poll
    if poll.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this poll"
        )
    
    # Delete the poll
    db.delete(poll)
    db.commit()
    
    # Return 204 No Content (already defined in the decorator)

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlmodel import Session, select, delete, func
from typing import Optional
from api.database import get_session
from api.auth.dependencies import get_current_user, get_current_user_optional
from api.public.user.models import UserRole
from api.public.community.models import Community, CommunityLevel
from api.public.community.crud import get_community_by_id
from api.public.country.crud import get_country_by_code
from api.public.region.crud import get_region_by_id
from api.public.subregion.crud import get_subregion_by_id
from api.public.locality.models import Locality
from api.public.tag.crud import get_tag_by_name, create_tag
from api.public.debate.models import (
    Debate, DebateCreate, DebateRead, DebateUpdate, 
    PointOfView, Opinion, 
    OpinionCreate, OpinionVote, OpinionVoteCreate,
    DebateType, DebateStatus,
    UserMinimal, OpinionRead, PointOfViewRead, CommunityMinimal,
    PaginatedDebateResponse,
    CommentCreate, CommentRead
)
from api.utils.slug import create_slug
from datetime import datetime
from api.public.country.models import Country
from sqlalchemy import text
from api.public.user.models import User
from api.public.community.models import UserCommunityLink, DebateCommunityLink

router = APIRouter()

@router.post("/", response_model=DebateRead, status_code=status.HTTP_201_CREATED)
def create_debate(
    debate_data: DebateCreate,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new debate"""
    
    # Generate the base slug from the title
    base_slug = create_slug(debate_data.title)
    
    # Check if the slug already exists and create a unique one
    slug = base_slug
    counter = 1
    
    # Check if the slug exists
    while session.exec(select(Debate).where(Debate.slug == slug)).first() is not None:
        # If it exists, create a new slug with a numeric suffix
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Create the debate with the unique slug
    new_debate = Debate(
        title=debate_data.title,
        description=debate_data.description,
        type=debate_data.type,
        slug=slug,  # Use the unique slug generated
        language=debate_data.language,
        public=debate_data.public,
        images=debate_data.images,
        is_anonymous=debate_data.is_anonymous,
        creator_id=current_user.id
    )
    
    session.add(new_debate)
    session.flush()  # To get the ID
    
    # Add tags
    for tag_name in debate_data.tags:
        tag = get_tag_by_name(session, tag_name)
        if not tag:
            tag = create_tag(session, tag_name)
        new_debate.tags.append(tag)
    
    # Add communities according to debate type
    if debate_data.type == DebateType.GLOBAL:
        # Global debate - add global community
        global_community = session.exec(
            select(Community).where(Community.level == CommunityLevel.GLOBAL)
        ).first()
        if global_community:
            new_debate.communities.append(global_community)
    
    elif debate_data.type == DebateType.INTERNATIONAL:
        # International debate - add country communities
        if not debate_data.country_codes:
            raise HTTPException(status_code=400, detail="Country codes are required for international debates")
        
        for code in debate_data.country_codes:
            country = get_country_by_code(session, code)
            if country and country.community:
                # Add the community to the debate
                new_debate.communities.append(country.community)
                
                # Automatically create a point of view for this country
                pov = PointOfView(
                    name=country.name,  # Use the country's name as the point of view name
                    debate_id=new_debate.id,
                    created_by_id=current_user.id,
                    community_id=country.community.id
                )
                session.add(pov)
    
    elif debate_data.type == DebateType.NATIONAL:
        # National debate - add national community
        if not debate_data.country_code:
            raise HTTPException(status_code=400, detail="Country code is required for national debates")
        
        country = get_country_by_code(session, debate_data.country_code)
        if country and country.community:
            new_debate.communities.append(country.community)
    
    elif debate_data.type == DebateType.REGIONAL:
        # Regional debate - add regional community
        if debate_data.region_id:
            # If region_id is provided, use it to get the community
            region = get_region_by_id(session, debate_data.region_id)
            if region and region.community:
                new_debate.communities.append(region.community)
        # If region_id is not provided, the provided community_ids will be used
    
    elif debate_data.type == DebateType.SUBREGIONAL:
        # Subregional debate - add subregional community
        if not debate_data.subregion_id:
            raise HTTPException(status_code=400, detail="Subregion ID is required for subregional debates")
        
        subregion = get_subregion_by_id(session, debate_data.subregion_id)
        if subregion and subregion.community:
            new_debate.communities.append(subregion.community)
    
    elif debate_data.type == DebateType.LOCAL:
        # Local debate - add local community
        if not debate_data.locality_id:
            raise HTTPException(status_code=400, detail="Locality ID is required for local debates")
        
        locality = session.get(Locality, debate_data.locality_id)
        if locality and locality.community:
            new_debate.communities.append(locality.community)
    
    # Add additional communities
    for community_id in debate_data.community_ids:
        # Convert to integer if it comes as a string
        try:
            community_id_int = int(community_id)
        except (ValueError, TypeError):
            # If it cannot be converted, use the original value
            community_id_int = community_id
            
        community = get_community_by_id(session, community_id_int)
        if community:
            new_debate.communities.append(community)
    
    # Add initial points of view
    for pov_data in debate_data.points_of_view:
        pov = PointOfView(
            name=pov_data.name,
            debate_id=new_debate.id,
            created_by_id=current_user.id
        )
        session.add(pov)
        session.flush()  # To get the ID
        
        # Add communities to the point of view if provided
        if hasattr(pov_data, 'community_ids'):
            for community_id in pov_data.community_ids:
                community = get_community_by_id(session, community_id)
                if community:
                    pov.communities.append(community)
    
    session.commit()
    session.refresh(new_debate)
    
    # Build response
    return get_debate_read(session, new_debate)

@router.get("/", response_model=PaginatedDebateResponse)
def get_debates(
    type: Optional[DebateType] = None,
    community_id: Optional[int] = None, 
    country_code: Optional[str] = None,
    region_id: Optional[int] = None,
    subregion_id: Optional[int] = None,
    locality_id: Optional[int] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    current_user = Depends(get_current_user_optional),
    session: Session = Depends(get_session)
):
    """Get debates with optional filters"""
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Base query
    query = select(Debate).where(Debate.deleted_at == None)
    
    # If community_id is provided, first determine which level of community it corresponds to
    if community_id:
        community = get_community_by_id(session, community_id)
        if community:
            # Apply filters according to the level of the community
            query = query.join(Community, Debate.communities).where(Community.id == community_id)
            
            # If it is a national community, filter by NATIONAL debates
            if community.level == CommunityLevel.NATIONAL:
                # Only apply this filter if no other type is explicitly specified
                if type is None:
                    query = query.where(Debate.type == DebateType.NATIONAL)
            # Similar for other community levels
            elif community.level == CommunityLevel.REGIONAL:
                if type is None:
                    query = query.where(Debate.type == DebateType.REGIONAL)
            elif community.level == CommunityLevel.SUBREGIONAL:
                if type is None:
                    query = query.where(Debate.type == DebateType.SUBREGIONAL)
            elif community.level == CommunityLevel.GLOBAL:
                if type is None:
                    query = query.where(Debate.type == DebateType.GLOBAL)
    # Apply explicit type filter if provided
    elif type:
        query = query.where(Debate.type == type)
    
    # Apply the rest of the filters as before
    if country_code:
        country = get_country_by_code(session, country_code)
        if country and country.community:
            query = query.join(Community, Debate.communities).where(Community.id == country.community.id)
    
    if region_id:
        region = get_region_by_id(session, region_id)
        if region and region.community:
            query = query.join(Community, Debate.communities).where(Community.id == region.community.id)
    
    if subregion_id:
        subregion = get_subregion_by_id(session, subregion_id)
        if subregion and subregion.community:
            query = query.join(Community, Debate.communities).where(Community.id == subregion.community.id)
    
    if locality_id:
        locality = session.get(Locality, locality_id)
        if locality and locality.community:
            query = query.join(Community, Debate.communities).where(Community.id == locality.community.id)
    
    if tag:
        query = query.join(Tag, Debate.tags).where(Tag.name == tag)
    
    if search:
        query = query.where(Debate.title.contains(search) | Debate.description.contains(search))
    
    # Count total for pagination
    total_query = select(func.count()).select_from(query.subquery())
    total = session.exec(total_query).first() or 0
    total_pages = (total + size - 1) // size  # Ceiling division
    
    # Order by creation date (most recent first)
    query = query.order_by(Debate.created_at.desc())
    
    # Apply pagination
    query = query.offset(offset).limit(size)
    
    debates = session.exec(query).all()
    
    # Prepare response with pagination metadata
    return {
        "items": [get_debate_read(session, debate, current_user) for debate in debates],
        "total": total,
        "page": page,
        "size": size,
        "pages": total_pages
    }

@router.get("/{debate_id_or_slug}", response_model=DebateRead)
def get_debate(
    debate_id_or_slug: str,
    current_user = Depends(get_current_user_optional),
    session: Session = Depends(get_session)
):
    """Get a specific debate by ID or slug"""
    # Determine if it is ID or slug
    if debate_id_or_slug.isdigit():
        debate = session.get(Debate, int(debate_id_or_slug))
    else:
        debate = session.exec(select(Debate).where(Debate.slug == debate_id_or_slug)).first()
    
    if not debate or debate.deleted_at:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    # Increment view count
    debate.views_count += 1
    session.commit()
    
    return get_debate_read(session, debate, current_user)

@router.patch("/{debate_id}", response_model=DebateRead)
def update_debate(
    debate_id: int,
    debate_update: DebateUpdate,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update an existing debate"""
    debate = session.get(Debate, debate_id)
    if not debate or debate.deleted_at:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    # Check permissions (only creator or admin)
    if debate.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You do not have permission to edit this debate")
    
    # Update basic fields
    update_data = debate_update.dict(exclude_unset=True)
    
    # Handle tags if provided
    if "tags" in update_data:
        tags = update_data.pop("tags")
        debate.tags.clear()
        for tag_name in tags:
            tag = get_tag_by_name(session, tag_name)
            if not tag:
                tag = create_tag(session, tag_name)
            debate.tags.append(tag)
    
    # Handle communities if provided
    if "community_ids" in update_data:
        community_ids = update_data.pop("community_ids")
        debate.communities.clear()
        for community_id in community_ids:
            community = get_community_by_id(session, community_id)
            if community:
                debate.communities.append(community)
    
    # Apply updates
    for key, value in update_data.items():
        setattr(debate, key, value)
    
    # Update modification date
    debate.updated_at = datetime.utcnow()
    
    session.commit()
    session.refresh(debate)
    
    return get_debate_read(session, debate)

@router.delete("/{debate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_debate(
    debate_id: int,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete (mark as deleted) a debate"""
    debate = session.get(Debate, debate_id)
    if not debate or debate.deleted_at:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    # Check permissions (only creator or admin)
    if debate.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this debate")
    
    # Mark as deleted
    debate.deleted_at = datetime.utcnow()
    session.commit()
    
    return None

@router.post("/{debate_id}/opinions", response_model=OpinionRead)
def add_opinion(
    debate_id: int,
    opinion_data: OpinionCreate,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Add an opinion to a debate, creating the point of view if necessary"""
    
    # Check that the debate exists
    debate = session.get(Debate, debate_id)
    if not debate or debate.deleted_at:
        raise HTTPException(status_code=404, detail="Debate not found")
    
    # Check that the debate is not closed
    if debate.status in [DebateStatus.CLOSED, DebateStatus.ARCHIVED, DebateStatus.RESOLVED]:
        raise HTTPException(status_code=400, detail="Cannot add opinions to closed or archived debates")
    
    # Check if the user has already opined in this debate
    existing_opinion = session.exec(
        select(Opinion)
        .join(PointOfView)
        .where(
            PointOfView.debate_id == debate_id,
            Opinion.user_id == current_user.id
        )
    ).first()
    
    if existing_opinion:
        raise HTTPException(
            status_code=400, 
            detail="You have already opined in this debate. Only one opinion per user is allowed."
        )
    
    # Handle obtaining the community_id according to the type of debate
    if debate.type in [DebateType.GLOBAL, DebateType.INTERNATIONAL]:
        if not opinion_data.country_cca2:
            raise HTTPException(
                status_code=400, 
                detail="For global and international debates, country_cca2 is required"
            )
        
        # Find the country by cca2
        country = session.exec(
            select(Country)
            .where(Country.cca2 == opinion_data.country_cca2)
        ).first()
        
        if not country:
            raise HTTPException(status_code=404, detail="Country not found")
        
        community_id = country.community_id
    elif debate.type == DebateType.NATIONAL:
        # For national debates, we use region_id
        if not opinion_data.region_id:
            raise HTTPException(status_code=400, detail="region_id is required for national debates")
        
        # Find the region by ID
        region = get_region_by_id(session, opinion_data.region_id)
        if not region:
            raise HTTPException(status_code=404, detail="Region not found")
        
        community_id = region.community_id
    else:
        if not opinion_data.community_id:
            raise HTTPException(status_code=400, detail="community_id is required for this type of debate")
        community_id = opinion_data.community_id
    
    # Check that the community exists
    community = get_community_by_id(session, community_id)
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    # Check if a point of view already exists for this debate and community
    pov = session.exec(
        select(PointOfView)
        .where(
            PointOfView.debate_id == debate_id,
            PointOfView.community_id == community_id
        )
    ).first()
    
    # If the point of view does not exist, create it
    if not pov:
        pov = PointOfView(
            name=community.name,  # Use the community's name as the point of view name
            debate_id=debate_id,
            created_by_id=current_user.id,
            community_id=community_id
        )
        session.add(pov)
        session.flush()  # To get the ID
    
    # Create the opinion
    new_opinion = Opinion(
        point_of_view_id=pov.id,
        user_id=current_user.id,
        content=opinion_data.content
    )
    
    session.add(new_opinion)
    session.commit()
    session.refresh(new_opinion)
    
    return get_opinion_read(session, new_opinion, current_user)

@router.post("/opinions/{opinion_id}/vote", response_model=OpinionRead)
def vote_opinion(
    opinion_id: int,
    vote_data: OpinionVoteCreate,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Vote an opinion (positive or negative)"""
    opinion = session.get(Opinion, opinion_id)
    if not opinion:
        raise HTTPException(status_code=404, detail="Opinion not found")
    
    # Check if the user has already voted this opinion
    existing_vote = session.exec(
        select(OpinionVote)
        .where(OpinionVote.opinion_id == opinion_id, OpinionVote.user_id == current_user.id)
    ).first()
    
    if existing_vote:
        # Update existing vote
        existing_vote.value = vote_data.value
    else:
        # Create new vote
        new_vote = OpinionVote(
            opinion_id=opinion_id,
            user_id=current_user.id,
            value=vote_data.value
        )
        session.add(new_vote)
    
    session.commit()
    session.refresh(opinion)
    
    return get_opinion_read(session, opinion, current_user)

@router.delete("/opinions/{opinion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opinion(
    opinion_id: int,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete an opinion from a debate (only the owner or admin)"""
    
    # Check that the opinion exists
    opinion = session.get(Opinion, opinion_id)
    if not opinion:
        raise HTTPException(status_code=404, detail="Opinion not found")
    
    # Check that the user is the owner of the opinion or an admin
    if opinion.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, 
            detail="You do not have permission to delete this opinion"
        )
    
    # Check if the debate is closed or archived
    point_of_view = session.get(PointOfView, opinion.point_of_view_id)
    if point_of_view:
        debate = session.get(Debate, point_of_view.debate_id)
        if debate and debate.status in [DebateStatus.CLOSED, DebateStatus.ARCHIVED, DebateStatus.RESOLVED]:
            raise HTTPException(
                status_code=400, 
                detail="Opinions cannot be deleted in closed or archived debates"
            )
    
    # First delete all votes associated with this opinion
    session.exec(
        delete(OpinionVote)
        .where(OpinionVote.opinion_id == opinion_id)
    )
    
    # Delete the opinion
    session.delete(opinion)
    session.commit()
    
    return None

@router.post("/{debate_id}/points-of-view/{pov_id}/opinions", response_model=OpinionRead)
def create_opinion(
    debate_id: int,
    pov_id: int,
    opinion_data: OpinionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a new opinion in a point of view.
    Requires authentication and membership in the debate community.
    """
    # Check that the debate exists
    debate = db.get(Debate, debate_id)
    if not debate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debate not found"
        )

    # Check that the user is a member of at least one of the debate communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    user_community_ids = set(uc.community_id for uc in user_communities)
    
    debate_communities = db.exec(
        select(DebateCommunityLink.community_id)
        .where(DebateCommunityLink.debate_id == debate_id)
    ).all()
    debate_community_ids = set(dc.community_id for dc in debate_communities)
    
    if not user_community_ids.intersection(debate_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to opine in this debate"
        )

    # Check that the point of view exists and belongs to the debate
    point_of_view = db.get(PointOfView, pov_id)
    if not point_of_view or point_of_view.debate_id != debate_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Point of view not found"
        )

    # Rest of the existing code...
    # [Previous validation code remains unchanged]

@router.post("/{debate_id}/points-of-view/{pov_id}/opinions/{opinion_id}/vote")
def vote_opinion(
    debate_id: int,
    pov_id: int,
    opinion_id: int,
    vote_value: int = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Vote an opinion (1 for positive, -1 for negative).
    Requires authentication and membership in the debate community.
    """
    # Check that the debate exists
    debate = db.get(Debate, debate_id)
    if not debate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debate not found"
        )

    # Check that the user is a member of at least one of the debate communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    user_community_ids = set(uc.community_id for uc in user_communities)
    
    debate_communities = db.exec(
        select(DebateCommunityLink.community_id)
        .where(DebateCommunityLink.debate_id == debate_id)
    ).all()
    debate_community_ids = set(dc.community_id for dc in debate_communities)
    
    if not user_community_ids.intersection(debate_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to vote in this debate"
        )

    # Rest of the existing code...
    # [Previous validation code remains unchanged]

@router.post("/{debate_id}/comments", response_model=CommentRead)
def create_debate_comment(
    debate_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a new comment in the debate.
    Requires authentication and membership in the debate community.
    """
    # Check that the debate exists
    debate = db.get(Debate, debate_id)
    if not debate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debate not found"
        )

    # Check that the user is a member of at least one of the debate communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    user_community_ids = set(uc.community_id for uc in user_communities)
    
    debate_communities = db.exec(
        select(DebateCommunityLink.community_id)
        .where(DebateCommunityLink.debate_id == debate_id)
    ).all()
    debate_community_ids = set(dc.community_id for dc in debate_communities)
    
    if not user_community_ids.intersection(debate_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to comment in this debate"
        )

    # Rest of the existing code...
    # [Previous validation code remains unchanged]

# Helper functions to build responses

def get_debate_read(session, debate, current_user=None):
    """Build DebateRead object from a debate in the database"""
    
    # Get the communities with their cca2 if applicable
    communities = []
    for community in debate.communities:
        # Find the country associated with this community if the debate is international or national
        cca2 = None
        if debate.type in [DebateType.INTERNATIONAL, DebateType.NATIONAL]:
            # Execute a query to get the country related to the community
            country = session.exec(
                select(Country)
                .where(Country.community_id == community.id)
            ).first()
            if country:
                cca2 = country.cca2
                
        communities.append(CommunityMinimal(
            id=community.id,
            name=community.name,
            cca2=cca2
        ))

    # Determine if we should show the creator's data
    creator = None  # By default we do not show the creator (anonymous)
    
    # We only show the creator if the debate is not anonymous OR if the current user is the creator/admin
    if not debate.is_anonymous or (current_user and (current_user.id == debate.creator_id or current_user.role == UserRole.ADMIN)):
        creator = UserMinimal(
            id=debate.creator.id,
            username=debate.creator.username,
            image=debate.creator.image
        )

    return DebateRead(
        id=debate.id,
        title=debate.title,
        description=debate.description,
        slug=debate.slug,
        type=debate.type,
        status=debate.status,
        public=debate.public,
        language=debate.language,
        images=debate.images,
        views_count=debate.views_count,
        created_at=debate.created_at,
        updated_at=debate.updated_at,
        creator=creator,  # Now it can be None if anonymous
        communities=communities,
        tags=[tag.name for tag in debate.tags],
        points_of_view=[
            get_point_of_view_read(session, pov, current_user)
            for pov in debate.points_of_view
        ],
        is_anonymous=debate.is_anonymous
    )

def get_point_of_view_read(session, pov, current_user=None):
    """Build PointOfViewRead object from a PointOfView in the database"""
    # Get the cca2 if it is a national or international debate
    cca2 = None
    if pov.debate.type in [DebateType.GLOBAL, DebateType.INTERNATIONAL]:
        # Execute a query to get the country related to the community
        country = session.exec(
            select(Country)
            .where(Country.community_id == pov.community_id)
        ).first()
        if country:
            cca2 = country.cca2

    return PointOfViewRead(
        id=pov.id,
        name=pov.name,
        created_at=pov.created_at,
        created_by=UserMinimal(
            id=pov.created_by.id,
            username=pov.created_by.username,
            image=pov.created_by.image
        ),
        community=CommunityMinimal(
            id=pov.community.id,
            name=pov.community.name,
            cca2=cca2
        ) if pov.community else None,
        opinions=[
            get_opinion_read(session, opinion, current_user)
            for opinion in pov.opinions
        ]
    )

def get_opinion_read(session, opinion, current_user=None):
    """Build OpinionRead object from an Opinion in the database with optional user vote"""
    upvotes = sum(1 for vote in opinion.votes if vote.value == 1)
    downvotes = sum(1 for vote in opinion.votes if vote.value == -1)
    score = sum(vote.value for vote in opinion.votes)
    
    # Check if the current user has voted on this opinion
    user_vote = None
    if current_user:
        # Find the current user's vote
        for vote in opinion.votes:
            if vote.user_id == current_user.id:
                user_vote = vote.value
                break
    
    return OpinionRead(
        id=opinion.id,
        content=opinion.content,
        created_at=opinion.created_at,
        updated_at=opinion.updated_at,
        user=UserMinimal(
            id=opinion.user.id,
            username=opinion.user.username,
            image=opinion.user.image
        ),
        upvotes=upvotes,
        downvotes=downvotes,
        score=score,
        user_vote=user_vote
    )

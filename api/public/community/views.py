from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlmodel import Session, select
from api.public.community.models import CommunityRead, CommunityLevel
from api.public.community.crud import get_community
from api.database import get_session
from sqlalchemy import func, delete, or_
from api.public.user.models import User, UserCommunityLink
from api.auth.dependencies import get_current_user_optional, get_current_user
from typing import Optional
from pydantic import BaseModel
import datetime
import unicodedata

from api.utils.pagination import PaginatedResponse

from api.public.community.models import CommunityRequest
from api.public.community.crud import create_community_request, get_community_requests, update_community_request_status
from api.public.region.models import Region
from api.public.community.models import Community

router = APIRouter()

@router.get("/search", response_model=CommunityRead)
def search_community(
    level: CommunityLevel,
    country: Optional[str] = None,
    region: Optional[str] = None,
    subregion: Optional[str] = None,
    local: Optional[str] = None,
    locality: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """
    Searches for a community by level and geographical criteria.
    Returns the data of the found community.
    
    Usage examples:
    - /communities/search?level=NATIONAL&country=argentina
    - /communities/search?level=REGIONAL&country=argentina&region=buenos-aires
    - /communities/search?level=SUBREGIONAL&country=argentina&region=buenos-aires&subregion=alberti
    - /communities/search?level=LOCAL&country=argentina&region=buenos-aires&subregion=caba&local=palermo
    """
    from api.public.community.models import Community
    import unicodedata
    
    def normalize_text(text):
        if not text:
            return None
        # Convert to lowercase
        text = text.lower()
        # Replace hyphens and underscores with spaces
        text = text.replace('-', ' ').replace('_', ' ')
        # Normalize accented characters
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
        return text
    
    normalized_country = normalize_text(country) if country else None
    normalized_region = normalize_text(region) if region else None
    normalized_subregion = normalize_text(subregion) if subregion else None
    
    local_param = local if local is not None else locality
    normalized_local = normalize_text(local_param) if local_param else None
    
    required_params = {
        CommunityLevel.NATIONAL: [("country", normalized_country)],
        CommunityLevel.REGIONAL: [("country", normalized_country), ("region", normalized_region)],
        CommunityLevel.SUBREGIONAL: [("country", normalized_country), ("region", normalized_region), 
                                   ("subregion", normalized_subregion)],
        CommunityLevel.LOCAL: [("country", normalized_country), ("local", normalized_local)]
    }
    
    if level in required_params:
        for param_name, param_value in required_params[level]:
            if not param_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"The '{param_name}' parameter is required for {level} level"
                )
    
    # Obtener todas las comunidades de ese nivel
    communities = db.query(Community).filter(Community.level == level).all()
    
    # Realizar la comparación en Python después de normalizar
    selected_community = None
    search_term = None
    
    if level == CommunityLevel.NATIONAL:
        search_term = normalized_country
    elif level == CommunityLevel.REGIONAL:
        search_term = normalized_region
    elif level == CommunityLevel.SUBREGIONAL:
        search_term = normalized_subregion
    elif level == CommunityLevel.LOCAL:
        search_term = normalized_local
    
    for community in communities:
        community_name = normalize_text(community.name)
        if community_name == search_term:
            selected_community = community
            break
    
    # Si no encontramos coincidencia exacta, intentamos búsqueda parcial
    if not selected_community and search_term:
        for community in communities:
            community_name = normalize_text(community.name)
            if search_term in community_name or community_name in search_term:
                selected_community = community
                break
    
    if not selected_community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No community found with the specified criteria"
        )
    
    # El objeto community es ya una instancia de Community
    result = CommunityRead.from_orm(selected_community)
    
    # Añadir region_id si el nivel de comunidad es REGIONAL
    if selected_community.level == CommunityLevel.REGIONAL:
        # Query the region table to find the region associated with this community
        region_data = db.exec(
            select(Region).where(Region.community_id == selected_community.id)
        ).first()
        
        if region_data:
            # Add the region_id to the response
            result_dict = result.dict()
            result_dict["region_id"] = region_data.id
            # Convert back to the response model
            result = CommunityRead(**result_dict)
    
    # Añadir subregion_id si el nivel de comunidad es SUBREGIONAL
    elif selected_community.level == CommunityLevel.SUBREGIONAL:
        # Query the subregion table to find the subregion associated with this community
        from api.public.subregion.models import Subregion
        subregion_data = db.exec(
            select(Subregion).where(Subregion.community_id == selected_community.id)
        ).first()
        
        if subregion_data:
            # Add the subregion_id to the response
            result_dict = result.dict()
            result_dict["subregion_id"] = subregion_data.id
            # Convert back to the response model
            result = CommunityRead(**result_dict)
    
    return result

@router.get("/{community_id}", response_model=CommunityRead)
def read(community_id: int, db: Session = Depends(get_session)):
    return get_community(community_id, db)

@router.get("/{community_id}/members", response_model=PaginatedResponse)
def get_community_members(
    community_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Get all members of a community.
    Optionally filter by public/private membership.
    """
    # Verify that the community exists
    community = db.get(Community, community_id)
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community not found"
        )
    
    # Get user's membership status if authenticated
    user_community_result = None
    if current_user:
        user_community_result = db.exec(
            select(UserCommunityLink.is_public)
            .where(
                UserCommunityLink.user_id == current_user.id,
                UserCommunityLink.community_id == community_id
            )
        ).first()
    
    current_user_is_public = user_community_result
    
    # Calculate offset for pagination
    offset = (page - 1) * size
    
    # Query that only selects members with is_public=True
    query = select(
        User.id,
        User.username,
        User.name,
        User.image,
        UserCommunityLink.is_public
    ).join(UserCommunityLink).where(
        UserCommunityLink.community_id == community_id,
        UserCommunityLink.is_public == True
    )
    
    # Execute query and process results - only public users
    rows = db.exec(query.offset(offset).limit(size)).all()
    user_list = []
    for row in rows:
        user_data = {
            "id": row.id,
            "username": row.username,
            "name": row.name,
            "image": row.image,
            "is_current_user": current_user and row.id == current_user.id,
            "is_public": row.is_public
        }
        user_list.append(user_data)
    
    # Count the total number of public members
    total_public_query = select(func.count()).where(
        UserCommunityLink.community_id == community_id,
        UserCommunityLink.is_public == True
    ).select_from(UserCommunityLink)
    total_public_result = db.exec(total_public_query).first()
    total_public = 0 if total_public_result is None else total_public_result
    
    # Count the total number of anonymous members (is_public=False)
    total_anonymous_query = select(func.count()).where(
        UserCommunityLink.community_id == community_id,
        UserCommunityLink.is_public == False
    ).select_from(UserCommunityLink)
    total_anonymous_result = db.exec(total_anonymous_query).first()
    total_anonymous = 0 if total_anonymous_result is None else total_anonymous_result
    
    # Check if the current user is set as not public in this community
    current_user_is_member = False
    
    if current_user:
        # Modify this query to ensure it returns exactly the field we need
        user_community_query = select(UserCommunityLink.is_public).where(
            UserCommunityLink.user_id == current_user.id,
            UserCommunityLink.community_id == community_id
        )
        user_community_result = db.exec(user_community_query).first()
        
        # Check if we got a result and access the is_public value safely
        if user_community_result:
            # The user is a member of the community
            current_user_is_member = True
            # Access the selected field directly
            current_user_is_public = user_community_result
    
    total = total_public
    pages = (total + size - 1) // size if size > 0 else 0
    has_more = page < pages
    
    # Build the response
    response = {
        "items": user_list,
        "total": total,
        "total_public": total_public,
        "total_anonymous": total_anonymous,
        "page": page,
        "size": size,
        "pages": pages,
        "has_more": has_more
    }
    
    # Add information about the current user only if authenticated
    if current_user:
        # Add the requested key at the root level
        response["is_public_current_user"] = current_user_is_public if current_user_is_member else False
        
        response["current_user"] = {
            "is_member": current_user_is_member,
            "is_public": current_user_is_member and current_user_is_public
        }
    
    return response

@router.post("/{community_id}/join", status_code=status.HTTP_200_OK)
def join_community(
    community_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Allows a user to join a community.
    By default, the user joins in private mode (is_public=False).
    """
    # Verify that the community exists
    community = get_community(community_id, db, check_membership=False, current_user=current_user)
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Community with ID {community_id} not found"
        )
    
    # Check if the user is already a member
    existing_membership = db.exec(
        select(UserCommunityLink).where(
            UserCommunityLink.user_id == current_user.id,
            UserCommunityLink.community_id == community_id
        )
    ).first()
    
    if existing_membership:
        return {"message": "You are already a member of this community"}
    
    # Create the user-community relationship (by default in private mode)
    new_membership = UserCommunityLink(
        user_id=current_user.id,
        community_id=community_id,
        is_public=False  # By default, the user is private in the community
    )
    
    db.add(new_membership)
    db.commit()
    
    return {"message": "You have joined the community successfully"}

@router.delete("/{community_id}/join", status_code=status.HTTP_200_OK)
def leave_community(
    community_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Allows a user to leave a community.
    """
    # Verify that the membership exists
    membership = db.exec(
        select(UserCommunityLink).where(
            UserCommunityLink.user_id == current_user.id,
            UserCommunityLink.community_id == community_id
        )
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this community"
        )
    
    # Delete the membership using delete statement
    db.exec(
        delete(UserCommunityLink).where(
            UserCommunityLink.user_id == current_user.id,
            UserCommunityLink.community_id == community_id
        )
    )
    db.commit()
    
    return {"message": "You have left the community successfully"}

# Pydantic model to validate the request
class CommunityRequestCreate(BaseModel):
    country: str
    region: str
    city: str
    email: str

# Model for responses
class CommunityRequestResponse(BaseModel):
    id: int
    country: str
    region: str
    city: str
    email: str
    status: str
    created_at: datetime.datetime
    
    model_config = {"from_attributes": True}

@router.post("/requests/", response_model=CommunityRequestResponse)
def create_community_request_endpoint(request: CommunityRequestCreate, db: Session = Depends(get_session)):
    """
    Endpoint to receive requests for new communities
    """
    try:
        request_data = request.dict()
        community_request = create_community_request(db, request_data)
        return community_request
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating the request: {str(e)}")

@router.get("/requests/", response_model=list[CommunityRequestResponse])
def get_community_requests_endpoint(
    skip: int = 0, 
    limit: int = 100, 
    status: Optional[str] = None, 
    db: Session = Depends(get_session)
):
    """
    Endpoint to get all community requests (with optional filter)
    """
    return get_community_requests(db, skip, limit, status)

@router.put("/requests/{request_id}/status")
def update_request_status(request_id: int, status: str, db: Session = Depends(get_session)):
    """
    Endpoint to update the status of a request
    """
    updated_request = update_community_request_status(db, request_id, status)
    if not updated_request:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"message": "Status updated successfully", "status": status}
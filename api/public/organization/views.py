from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import Optional
from api.database import get_session
from api.auth.dependencies import get_current_user
from api.public.user.models import User, UserRole
from .models import Organization, OrganizationCreate, OrganizationRead
from .crud import get_all_organizations, create_organization, get_organization_by_id, update_organization, delete_organization

router = APIRouter()

@router.get("/")
def read_organizations(
    level: Optional[str] = None,
    community_id: Optional[int] = None,
    region_id: Optional[int] = None,
    subregion_id: Optional[int] = None,
    locality_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_session)
):
    """
    Get organizations with optional filters and pagination.
    """
    return get_all_organizations(
        db,
        level=level,
        community_id=community_id,
        region_id=region_id,
        subregion_id=subregion_id,
        locality_id=locality_id,
        search=search,
        page=page,
        size=size
    )

@router.post("/", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_new_organization(
    organization_data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a new organization.
    Only administrators can create organizations.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create organizations"
        )
    
    return create_organization(db, organization_data)

@router.get("/{organization_id}", response_model=OrganizationRead)
def get_organization(
    organization_id: int,
    db: Session = Depends(get_session)
):
    """
    Get a specific organization by ID.
    """
    return get_organization_by_id(db, organization_id)

@router.patch("/{organization_id}", response_model=OrganizationRead)
def update_organization_details(
    organization_id: int,
    organization_data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update an existing organization.
    Only administrators can update organizations.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update organizations"
        )
    
    return update_organization(db, organization_id, organization_data.dict())

@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization_endpoint(
    organization_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete an organization.
    Only administrators can delete organizations.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete organizations"
        )
    
    delete_organization(db, organization_id) 
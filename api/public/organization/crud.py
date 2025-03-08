from sqlmodel import Session, select, func
from fastapi import HTTPException, status
from math import ceil
from .models import Organization, OrganizationCreate, OrganizationRead

def create_organization(db: Session, organization_data: OrganizationCreate) -> Organization:
    """
    Creates a new organization
    """
    new_organization = Organization(**organization_data.dict())
    db.add(new_organization)
    db.commit()
    db.refresh(new_organization)
    return new_organization

def get_organization_by_id(db: Session, organization_id: int) -> Organization:
    """
    Gets an organization by ID
    """
    organization = db.get(Organization, organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return organization

def get_all_organizations(
    db: Session,
    level = None,
    community_id = None,
    region_id = None,
    subregion_id = None,
    locality_id = None,
    search = None,
    page: int = 1,
    size: int = 10
):
    """
    Gets all organizations with optional filters
    """
    # Calculate offset for pagination
    offset = (page - 1) * size

    # First, get the total number of organizations for pagination
    total_query = select(func.count(Organization.id)).where(Organization.id > 0)
    
    if level:
        total_query = total_query.where(Organization.level == level)
    
    if community_id:
        total_query = total_query.where(Organization.community_id == community_id)
    
    if region_id:
        total_query = total_query.where(Organization.region_id == region_id)
    
    if subregion_id:
        total_query = total_query.where(Organization.subregion_id == subregion_id)
    
    if locality_id:
        total_query = total_query.where(Organization.locality_id == locality_id)
    
    if search:
        total_query = total_query.where(
            Organization.name.contains(search) | Organization.description.contains(search)
        )
    
    total = db.exec(total_query).first() or 0
    total_pages = ceil(total / size)

    # Main query to get the organizations
    organizations_query = select(Organization).where(Organization.id > 0)
    
    if level:
        organizations_query = organizations_query.where(Organization.level == level)
    
    if community_id:
        organizations_query = organizations_query.where(Organization.community_id == community_id)
    
    if region_id:
        organizations_query = organizations_query.where(Organization.region_id == region_id)
    
    if subregion_id:
        organizations_query = organizations_query.where(Organization.subregion_id == subregion_id)
    
    if locality_id:
        organizations_query = organizations_query.where(Organization.locality_id == locality_id)
    
    if search:
        organizations_query = organizations_query.where(
            Organization.name.contains(search) | Organization.description.contains(search)
        )
    
    # Add sorting and pagination
    organizations_query = organizations_query.order_by(Organization.name).offset(offset).limit(size)
    
    organizations = db.exec(organizations_query).all()
    
    return {
        "items": organizations,
        "total": total,
        "page": page,
        "size": size,
        "pages": total_pages
    }

def update_organization(db: Session, organization_id: int, organization_data: dict) -> Organization:
    """
    Updates an organization
    """
    organization = get_organization_by_id(db, organization_id)
    
    # Update the organization with provided data
    for key, value in organization_data.items():
        setattr(organization, key, value)
    
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization

def delete_organization(db: Session, organization_id: int) -> None:
    """
    Deletes an organization
    """
    organization = get_organization_by_id(db, organization_id)
    db.delete(organization)
    db.commit() 
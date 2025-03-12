from sqlmodel import Session, select
from typing import Optional
from api.public.region.models import Region

def get_region_by_id(session: Session, region_id: int) -> Optional[Region]:
    """
    Gets a region by its ID
    
    Args:
        session: Database session
        region_id: ID of the region to search for
        
    Returns:
        Region object if found, None otherwise
    """
    return session.get(Region, region_id)

def get_regions(session: Session, skip: int = 0, limit: int = 100) -> list[Region]:
    """
    Gets a list of regions with pagination
    
    Args:
        session: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Region objects
    """
    return session.exec(select(Region).offset(skip).limit(limit)).all()

def create_region(session: Session, region_data: dict) -> Region:
    """
    Creates a new region
    
    Args:
        session: Database session
        region_data: Dictionary with the region data
        
    Returns:
        Created Region object
    """
    region = Region(**region_data)
    session.add(region)
    session.commit()
    session.refresh(region)
    return region 
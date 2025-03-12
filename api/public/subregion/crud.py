from sqlmodel import Session, select
from typing import Optional
from api.public.subregion.models import Subregion

def get_subregion_by_id(session: Session, subregion_id: int) -> Optional[Subregion]:
    """
    Get a subregion by its ID
    
    Args:
        session: Database session
        subregion_id: ID of the subregion to search for
        
    Returns:
        Subregion object if found, None otherwise
    """
    return session.get(Subregion, subregion_id)

def get_subregions(session: Session, region_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> list[Subregion]:
    """
    Get a list of subregions, optionally filtered by region
    
    Args:
        session: Database session
        region_id: Optional ID of the region to filter
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Subregion objects
    """
    query = select(Subregion)
    if region_id:
        query = query.where(Subregion.region_id == region_id)
    return session.exec(query.offset(skip).limit(limit)).all()

def create_subregion(session: Session, subregion_data: dict) -> Subregion:
    """
    Create a new subregion
    
    Args:
        session: Database session
        subregion_data: Dictionary with the subregion data
        
    Returns:
        Created Subregion object
    """
    subregion = Subregion(**subregion_data)
    session.add(subregion)
    session.commit()
    session.refresh(subregion)
    return subregion 
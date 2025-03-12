from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Optional

from api.database import get_session
from api.public.region.models import Region
from api.public.subregion.models import Subregion

router = APIRouter()

@router.get("/{region_id}/subregions", response_model=list[Subregion])
def get_region_subregions(
    region_id: int,
    name: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """
    Retrieves all subregions of a specific region using its ID.
    Optionally, it can filter by subregion name.
    """
    # First, we check that the region exists
    region = db.get(Region, region_id)
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region with ID {region_id} not found"
        )

    # We build the base query
    query = select(Subregion).where(Subregion.region_id == region_id)
    
    # If a name is provided, we add the filter
    if name:
        query = query.where(Subregion.name.ilike(f"%{name}%"))

    # We execute the query
    subregions = db.exec(query).all()
    
    if not subregions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No subregions found for the region with ID {region_id}"
        )
    
    return subregions

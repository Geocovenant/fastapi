from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from api.database import get_session
from api.public.subregion.models import Subregion
from api.public.locality.models import Locality
router = APIRouter()

@router.get("/{subregion_id}/localities", response_model=list[Subregion])
def get_divisions_by_region(
    subregion_id: int,
    db: Session = Depends(get_session)
):
    """
    Retrieves all divisions of a specific subnation by its ID
    """
    # First, we check that the subregion exists
    subregion = db.get(Subregion, subregion_id)
    if not subregion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subregion with ID {subregion_id} not found"
        )
    localities = db.exec(
        select(Locality).where(Locality.subregion_id == subregion_id)
    ).all()
    
    if not localities:
        raise HTTPException(
            status_code=404,
            detail=f"No divisions found for the subregion with ID {subregion_id}"
        )
    
    return localities 
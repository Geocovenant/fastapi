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
    Obtiene todas las divisiones de una subnación específica por su ID
    """
    # Primero verificamos que la región existe
    subregion = db.get(Subregion, subregion_id)
    if not subregion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la región con ID {subregion_id}"
        )
    localities = db.exec(
        select(Locality).where(Locality.subregion_id == subregion_id)
    ).all()
    
    if not localities:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron divisiones para la región con ID {subregion_id}"
        )
    
    return localities 
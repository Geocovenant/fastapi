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
    Obtiene todas las subregiones de una región específica usando su ID.
    Opcionalmente puede filtrar por nombre de subregión.
    """
    # Primero verificamos que la región existe
    region = db.get(Region, region_id)
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la región con ID {region_id}"
        )

    # Construimos la consulta base
    query = select(Subregion).where(Subregion.region_id == region_id)
    
    # Si se proporciona un nombre, agregamos el filtro
    if name:
        query = query.where(Subregion.name.ilike(f"%{name}%"))

    # Ejecutamos la consulta
    subregions = db.exec(query).all()
    
    if not subregions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron subregiones para la región con ID {region_id}"
        )
    
    return subregions

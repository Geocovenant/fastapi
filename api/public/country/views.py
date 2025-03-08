from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import datetime

from api.database import get_session
from api.public.country.models import Country
from api.public.country.crud import get_all_countries, get_country_by_name, get_country_by_code
from api.public.region.models import Region

router = APIRouter()

@router.get("/", response_model=list[Country])
def read_countries(db: Session = Depends(get_session)):
    return get_all_countries(db)

@router.get("/{country_code}", response_model=Country)
def read_country_by_code(country_code: str, db: Session = Depends(get_session)):
    """
    Obtiene un país utilizando su código CCA2 (ISO 3166-1 alpha-2)
    """
    country = get_country_by_code(db, country_code.upper())
    if not country:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="País no encontrado")
    return country

@router.get("/{country_code}/divisions", response_model=list[Region])
def get_country_divisions(
    country_code: str,
    db: Session = Depends(get_session)
):
    """
    Retrieves all divisions (subnations) of a specific country using its country code (cca2)
    """
    regions = db.exec(
        select(Region).where(Region.country_cca2 == country_code.upper())
    ).all()
    
    if not regions:
        raise HTTPException(
            status_code=404,
            detail=f"No divisions found for the country with code {country_code}"
        )
    
    return regions

# Modelo Pydantic para validar la solicitud
class CommunityRequestCreate(BaseModel):
    country: str
    region: str
    city: str
    email: str

# Modelo para las respuestas
class CommunityRequestResponse(BaseModel):
    id: int
    country: str
    region: str
    city: str
    email: str
    status: str
    created_at: datetime.datetime
    
    model_config = {"from_attributes": True}

@router.post("/community-requests/", response_model=CommunityRequestResponse)
def create_community_request(request: CommunityRequestCreate, db: Session = Depends(get_session)):
    """
    Endpoint para recibir solicitudes de nuevas comunidades
    """
    try:
        request_data = request.dict()
        community_request = create_community_request(db, request_data)
        return community_request
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear la solicitud: {str(e)}")

@router.get("/community-requests/", response_model=List[CommunityRequestResponse])
def get_community_requests(
    skip: int = 0, 
    limit: int = 100, 
    status: Optional[str] = None, 
    db: Session = Depends(get_session)
):
    """
    Endpoint para obtener todas las solicitudes de comunidades (con filtro opcional)
    """
    return get_community_requests(db, skip, limit, status)

@router.put("/community-requests/{request_id}/status")
def update_request_status(request_id: int, status: str, db: Session = Depends(get_session)):
    """
    Endpoint para actualizar el estado de una solicitud
    """
    updated_request = update_community_request_status(db, request_id, status)
    if not updated_request:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return {"message": "Estado actualizado correctamente", "status": status}
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from api.database import get_session
from api.public.country.models import Country
from api.public.country.crud import get_all_countries, get_country_by_name
from api.public.subnation.models import Subnation

router = APIRouter()

@router.get("/", response_model=list[Country])
def read_countries(db: Session = Depends(get_session)):
    return get_all_countries(db)

@router.get("/{country_name}", response_model=Country)
def read_country_by_name(country_name: str, db: Session = Depends(get_session)):
    country = get_country_by_name(db, country_name)
    if not country:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Country not found")
    return country

@router.get("/{country_code}/divisions", response_model=list[Subnation])
def get_country_divisions(
    country_code: str,
    db: Session = Depends(get_session)
):
    """
    Obtiene todas las divisiones (subnaciones) de un país específico usando su código de país (cca2)
    """
    subnations = db.exec(
        select(Subnation).where(Subnation.country_cca2 == country_code.upper())
    ).all()
    
    if not subnations:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron divisiones para el país con código {country_code}"
        )
    
    return subnations
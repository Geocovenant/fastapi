from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from api.database import get_session
from api.public.country.models import Country
from api.public.country.crud import get_all_countries, get_country_by_name
from api.public.region.models import Region

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
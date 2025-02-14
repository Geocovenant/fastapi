from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from api.public.country.models import Country
from api.database import get_session
from api.public.country.crud import get_all_countries, get_country_by_name

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
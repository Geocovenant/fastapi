from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import Session
from typing import Optional
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
    Retrieves a country using its CCA2 code (ISO 3166-1 alpha-2)
    """
    country = get_country_by_code(db, country_code.upper())
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

# Pydantic model to validate the request
class CommunityRequestCreate(BaseModel):
    country: str
    region: str
    city: str
    email: str

# Model for responses
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
    Endpoint to receive requests for new communities
    """
    try:
        request_data = request.dict()
        community_request = create_community_request(db, request_data)
        return community_request
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating the request: {str(e)}")

@router.get("/community-requests/", response_model=list[CommunityRequestResponse])
def get_community_requests(
    skip: int = 0, 
    limit: int = 100, 
    status: Optional[str] = None, 
    db: Session = Depends(get_session)
):
    """
    Endpoint to get all community requests (with optional filtering)
    """
    return get_community_requests(db, skip, limit, status)

@router.put("/community-requests/{request_id}/status")
def update_request_status(request_id: int, status: str, db: Session = Depends(get_session)):
    """
    Endpoint to update the status of a request
    """
    updated_request = update_community_request_status(db, request_id, status)
    if not updated_request:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"message": "Status updated successfully", "status": status}
from fastapi import APIRouter, Depends
from sqlmodel import Session
from api.database import get_session

router = APIRouter()

@router.get("/me")
def read_me(db: Session = Depends(get_session)):
    return []
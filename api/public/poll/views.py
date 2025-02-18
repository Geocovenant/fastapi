from fastapi import APIRouter, Depends, HTTPException
from api.database import get_session
from sqlmodel import Session
from api.public.user.models import User
from api.public.poll.crud import get_all_polls

router = APIRouter()

@router.get("/")
def read_polls(
    db: Session = Depends(get_session)
):
    return get_all_polls(db)
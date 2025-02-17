from fastapi import APIRouter, Depends, HTTPException
from api.public.poll.models import Poll, PollRead

router = APIRouter()

@router.get("/", response_model=list[PollRead])
def read_polls():
    return [{"data": "Polls"}]
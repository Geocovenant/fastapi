from fastapi import APIRouter, Depends, HTTPException, status
from api.database import get_session
from sqlmodel import Session
from api.public.user.models import User
from api.public.poll.crud import get_all_polls, create_poll, create_vote
from api.public.poll.models import PollCreate, PollRead, PollVoteCreate
from api.auth.dependencies import get_current_user

router = APIRouter()

@router.get("/")
def read_polls(
    scope: str | None = None,
    db: Session = Depends(get_session)
):
    return get_all_polls(db, scope=scope)

@router.post("/", response_model=PollRead, status_code=status.HTTP_201_CREATED)
def create_new_poll(
    poll_data: PollCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Crear una nueva encuesta.
    Requiere autenticación.
    """
    if len(poll_data.options) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La encuesta debe tener al menos 2 opciones"
        )
    
    return create_poll(db, poll_data, current_user.id)

@router.post("/{poll_id}/vote", response_model=PollRead)
def vote_poll(
    poll_id: int,
    vote_data: PollVoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Votar en una encuesta.
    Requiere autenticación.
    """
    return create_vote(db, poll_id, vote_data.option_ids, current_user.id)
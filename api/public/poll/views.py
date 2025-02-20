from fastapi import APIRouter, Depends, HTTPException, status
from api.database import get_session
from sqlmodel import Session
from api.public.user.models import User
from api.public.poll.crud import get_all_polls, create_poll, create_vote, create_or_update_reaction
from api.public.poll.models import (
    PollCreate, 
    PollRead, 
    PollVoteCreate,
    Poll,
    PollStatus, 
    PollType, 
    PollOption,
    PollVote,
    PollReactionCreate
)
from api.auth.dependencies import get_current_user
from datetime import datetime

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
    Si option_ids está vacío, elimina los votos existentes del usuario.
    Requiere autenticación.
    """
    # Primero obtener la encuesta
    poll = db.get(Poll, poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encuesta no encontrada"
        )
    
    # Validar el estado de la encuesta
    if poll.status != PollStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede votar en esta encuesta porque su estado es {poll.status}"
        )
    
    # Validar si la encuesta ha expirado
    if poll.ends_at and poll.ends_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Esta encuesta expiró el {poll.ends_at}"
        )

    # Si option_ids está vacío, solo eliminamos los votos existentes
    if len(vote_data.option_ids) == 0:
        # Buscar y eliminar votos existentes
        existing_votes = db.query(PollVote).filter(
            PollVote.poll_id == poll_id,
            PollVote.user_id == current_user.id
        ).all()
        
        # Decrementar contadores de votos y eliminar los votos
        for vote in existing_votes:
            option = db.get(PollOption, vote.option_id)
            if option:
                option.votes = max(0, option.votes - 1)
            db.delete(vote)
        
        db.commit()
        db.refresh(poll)
        return poll

    # Si hay option_ids, continuar con la validación normal...
    valid_options = []
    for option_id in vote_data.option_ids:
        option = db.query(PollOption).filter(
            PollOption.id == option_id,
            PollOption.poll_id == poll_id
        ).first()
        if not option:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La opción {option_id} no existe en la encuesta {poll_id}"
            )
        valid_options.append(option)

    # Validar el número de opciones según el tipo de encuesta
    if poll.type == PollType.BINARY or poll.type == PollType.SINGLE_CHOICE:
        if len(vote_data.option_ids) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este tipo de encuesta solo permite seleccionar una opción"
            )

    return create_vote(db, poll_id, vote_data.option_ids, current_user.id)

@router.post("/{poll_id}/react", response_model=PollRead)
def react_to_poll(
    poll_id: int,
    reaction_data: PollReactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Reaccionar a una encuesta con LIKE o DISLIKE.
    Si ya existe una reacción del mismo tipo, se elimina.
    Si existe una reacción diferente, se actualiza.
    Requiere autenticación.
    """
    return create_or_update_reaction(
        db, 
        poll_id, 
        current_user.id, 
        reaction_data.reaction
    )
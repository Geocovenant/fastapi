from fastapi import APIRouter, Depends, HTTPException, status, Header
from api.database import get_session
from sqlmodel import Session, select, func
from api.public.user.models import User
from api.public.poll.crud import get_all_polls, create_poll, create_vote, create_or_update_reaction, get_country_polls, get_regional_polls
from api.public.poll.models import (
    PollCreate, 
    PollRead, 
    PollVoteCreate,
    Poll,
    PollStatus, 
    PollType, 
    PollOption,
    PollVote,
    PollReactionCreate,
    PollComment,
    PollCommentCreate,
    PollCommentUpdate
)
from api.auth.dependencies import get_current_user, get_current_user_optional
from datetime import datetime
from api.public.country.models import Country
from api.public.subregion.models import Subregion
from api.public.community.models import Community
from api.public.region.models import Region

router = APIRouter()

@router.get("/")
def read_polls(
    scope: str | None = None,
    country: str | None = None,
    region: int | None = None,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Obtener encuestas con filtros opcionales.
    - scope: Filtrar por alcance (ej: 'NATIONAL', 'INTERNATIONAL', 'REGIONAL', etc.)
    - country: Filtrar por código de país (CCA2)
    - region: Filtrar por ID de región
    """
    if country:
        return get_country_polls(
            db,
            country_code=country,
            scope=scope,
            current_user_id=current_user.id if current_user else None
        )
    
    if region:
        # Verificar que la región existe
        region_obj = db.exec(
            select(Region)
            .where(Region.id == region)
        ).first()

        if not region_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró la región con ID {region}"
            )

        return get_regional_polls(
            db,
            region_id=region,
            scope=scope,
            current_user_id=current_user.id if current_user else None
        )
    
    return get_all_polls(
        db, 
        scope=scope, 
        current_user_id=current_user.id if current_user else None
    )

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

@router.get("/{poll_id}/comments")
def get_poll_comments(
    poll_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Obtener todos los comentarios de una encuesta específica.
    No requiere autenticación.
    """
    poll = db.get(Poll, poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encuesta no encontrada"
        )

    comments = db.exec(
        select(PollComment, User)
        .join(User)
        .where(PollComment.poll_id == poll_id)
        .order_by(PollComment.created_at.desc())
    ).all()

    return [
        {
            **comment.dict(),
            "username": user.username,
            "can_edit": current_user and current_user.id == comment.user_id
        }
        for comment, user in comments
    ]

@router.post("/{poll_id}/comments", status_code=status.HTTP_201_CREATED)
def create_poll_comment(
    poll_id: int,
    comment_data: PollCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Crear un nuevo comentario en una encuesta.
    Requiere autenticación.
    """
    poll = db.get(Poll, poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encuesta no encontrada"
        )

    new_comment = PollComment(
        poll_id=poll_id,
        user_id=current_user.id,
        content=comment_data.content,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return {
        **new_comment.dict(),
        "username": current_user.username,
        "can_edit": True
    }

@router.put("/{poll_id}/comments/{comment_id}")
def update_poll_comment(
    poll_id: int,
    comment_id: int,
    comment_data: PollCommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Actualizar un comentario existente.
    Solo el autor puede editar su comentario.
    """
    comment = db.get(PollComment, comment_id)
    if not comment or comment.poll_id != poll_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comentario no encontrado"
        )

    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para editar este comentario"
        )

    comment.content = comment_data.content
    comment.updated_at = datetime.utcnow()
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        **comment.dict(),
        "username": current_user.username,
        "can_edit": True
    }

@router.delete("/{poll_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_poll_comment(
    poll_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Eliminar un comentario.
    Solo el autor puede eliminar su comentario.
    """
    comment = db.get(PollComment, comment_id)
    if not comment or comment.poll_id != poll_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comentario no encontrado"
        )

    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este comentario"
        )

    db.delete(comment)
    db.commit()

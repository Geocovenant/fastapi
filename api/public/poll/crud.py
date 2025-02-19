from sqlmodel import Session, select
from api.public.poll.models import Poll, PollOption, PollCreate, PollVote
from api.public.community.models import Community
from slugify import slugify
from datetime import datetime
from fastapi import HTTPException, status
from api.public.poll.models import PollStatus, PollType
import random
import string

def get_all_polls(db: Session, scope: str | None = None):
    query = select(Poll, PollOption).join(PollOption)
    
    if scope:
        query = query.where(Poll.scope == scope)
    
    results = db.exec(query).all()
    
    polls_dict = {}
    for poll, option in results:
        if poll.id not in polls_dict:
            polls_dict[poll.id] = poll.dict()
            polls_dict[poll.id]['options'] = []
        polls_dict[poll.id]['options'].append(option.dict())
    
    return list(polls_dict.values())

def generate_unique_slug(db: Session, title: str) -> str:
    # Genera el slug base
    base_slug = slugify(title)
    slug = base_slug
    
    # Verifica si el slug existe
    while db.query(Poll).filter(Poll.slug == slug).first() is not None:
        # Si existe, añade un sufijo aleatorio
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        slug = f"{base_slug}-{random_suffix}"
    
    return slug

def create_poll(db: Session, poll_data: PollCreate, user_id: int) -> Poll:
    # Genera un slug único
    unique_slug = generate_unique_slug(db, poll_data.title)
    
    # Obtener el tiempo actual
    current_time = datetime.utcnow()
    
    # Crear la encuesta
    db_poll = Poll(
        **poll_data.dict(exclude={'options', 'community_ids'}),
        creator_id=user_id,
        slug=unique_slug,
        created_at=current_time,
        updated_at=current_time
    )
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    
    # Crear las opciones de la encuesta
    for option_data in poll_data.options:
        db_option = PollOption(
            poll_id=db_poll.id,
            **option_data.dict()
        )
        db.add(db_option)
    
    # Asociar las comunidades con la encuesta
    if poll_data.community_ids:
        communities = db.exec(
            select(Community).where(Community.id.in_(poll_data.community_ids))
        ).all()
        db_poll.communities.extend(communities)
    
    db.commit()
    db.refresh(db_poll)
    return db_poll

def create_vote(db: Session, poll_id: int, option_ids: list[int], user_id: int) -> Poll:
    # Verificar que la encuesta existe
    poll = db.get(Poll, poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encuesta no encontrada"
        )
    
    # Verificar que la encuesta está publicada
    if poll.status != PollStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede votar en una encuesta que no está publicada"
        )
    
    # Verificar que las opciones pertenecen a la encuesta
    valid_options = db.exec(
        select(PollOption).where(
            PollOption.poll_id == poll_id,
            PollOption.id.in_(option_ids)
        )
    ).all()
    
    if len(valid_options) != len(option_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Algunas opciones no son válidas para esta encuesta"
        )
    
    # Verificar el tipo de votación
    if poll.type == PollType.BINARY or poll.type == PollType.SINGLE_CHOICE:
        if len(option_ids) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta encuesta solo permite una opción"
            )
    
    # Buscar votos existentes del usuario en esta encuesta
    existing_votes = db.exec(
        select(PollVote).where(
            PollVote.poll_id == poll_id,
            PollVote.user_id == user_id
        )
    ).all()
    
    # Eliminar votos anteriores
    for vote in existing_votes:
        # Decrementar el contador de votos de la opción anterior
        old_option = db.get(PollOption, vote.option_id)
        old_option.votes = max(0, old_option.votes - 1)  # Evitar números negativos
        db.delete(vote)
    
    # Crear los nuevos votos
    for option_id in option_ids:
        vote = PollVote(
            poll_id=poll_id,
            option_id=option_id,
            user_id=user_id
        )
        db.add(vote)
        
        # Incrementar el contador de votos de la nueva opción
        option = db.get(PollOption, option_id)
        option.votes += 1
    
    db.commit()
    db.refresh(poll)
    return poll
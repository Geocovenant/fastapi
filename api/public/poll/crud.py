from sqlmodel import Session, select, func
from api.public.poll.models import Poll, PollOption, PollCreate, PollVote, PollReaction, ReactionType
from api.public.community.models import Community
from slugify import slugify
from datetime import datetime
from fastapi import HTTPException, status
from api.public.poll.models import PollStatus, PollType
import random
import string
from api.public.user.models import User

def get_all_polls(db: Session, scope: str | None = None):
    # Primero obtenemos el conteo de reacciones por tipo para cada encuesta
    reactions_count = db.exec(
        select(
            PollReaction.poll_id,
            PollReaction.reaction,
            func.count(PollReaction.id).label('count')
        ).group_by(
            PollReaction.poll_id,
            PollReaction.reaction
        )
    ).all()
    
    # Creamos un diccionario para almacenar los conteos
    reactions_dict = {}
    for reaction in reactions_count:
        if reaction.poll_id not in reactions_dict:
            reactions_dict[reaction.poll_id] = {'LIKE': 0, 'DISLIKE': 0}
        reactions_dict[reaction.poll_id][reaction.reaction] = reaction.count

    # Consulta principal para obtener encuestas, opciones y usuarios
    query = select(Poll, PollOption, User).join(PollOption).join(User, Poll.creator_id == User.id)
    
    if scope:
        query = query.where(Poll.scope == scope)
    
    results = db.exec(query).all()
    
    polls_dict = {}
    for poll, option, user in results:
        if poll.id not in polls_dict:
            poll_dict = poll.dict()
            # Reemplazar creator_id con username si no es anónima
            if not poll.is_anonymous:
                poll_dict['creator_username'] = user.username
                del poll_dict['creator_id']
            else:
                del poll_dict['creator_id']
            
            # Agregar conteo de reacciones
            poll_dict['reactions'] = reactions_dict.get(poll.id, {'LIKE': 0, 'DISLIKE': 0})
            
            polls_dict[poll.id] = poll_dict
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

def create_or_update_reaction(db: Session, poll_id: int, user_id: int, reaction_type: ReactionType) -> Poll:
    """
    Crea o actualiza una reacción en una encuesta.
    Si la reacción ya existe y es del mismo tipo, se elimina.
    Si la reacción ya existe y es de diferente tipo, se actualiza.
    """
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
            detail="No se puede reaccionar a una encuesta que no está publicada"
        )
    
    # Buscar si ya existe una reacción del usuario
    existing_reaction = db.exec(
        select(PollReaction).where(
            PollReaction.poll_id == poll_id,
            PollReaction.user_id == user_id
        )
    ).first()
    
    if existing_reaction:
        if existing_reaction.reaction == reaction_type:
            # Si la reacción es la misma, eliminarla
            db.delete(existing_reaction)
        else:
            # Si la reacción es diferente, actualizarla
            existing_reaction.reaction = reaction_type
            existing_reaction.reacted_at = datetime.utcnow()
            db.add(existing_reaction)
    else:
        # Crear nueva reacción
        new_reaction = PollReaction(
            poll_id=poll_id,
            user_id=user_id,
            reaction=reaction_type,
            reacted_at=datetime.utcnow()
        )
        db.add(new_reaction)
    
    db.commit()
    
    # Obtener la encuesta actualizada con toda su información
    query = select(Poll, PollOption, User).join(PollOption).join(User, Poll.creator_id == User.id).where(Poll.id == poll_id)
    result = db.exec(query).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error al obtener la encuesta actualizada"
        )
    
    poll, option, user = result
    
    # Obtener el conteo actualizado de reacciones
    reactions_count = db.exec(
        select(
            PollReaction.reaction,
            func.count(PollReaction.id).label('count')
        ).where(
            PollReaction.poll_id == poll_id
        ).group_by(
            PollReaction.reaction
        )
    ).all()
    
    # Crear el diccionario de la encuesta
    poll_dict = poll.dict()
    if not poll.is_anonymous:
        poll_dict['creator_username'] = user.username
        del poll_dict['creator_id']
    else:
        del poll_dict['creator_id']
    
    # Agregar conteo de reacciones
    reactions_dict = {'LIKE': 0, 'DISLIKE': 0}
    for reaction in reactions_count:
        reactions_dict[reaction.reaction] = reaction.count
    
    poll_dict['reactions'] = reactions_dict
    
    # Obtener todas las opciones de la encuesta
    options = db.exec(
        select(PollOption).where(PollOption.poll_id == poll_id)
    ).all()
    poll_dict['options'] = [option.dict() for option in options]
    
    # Obtener las comunidades asociadas a la encuesta
    communities = [
        {"id": c.id, "name": c.name, "description": c.description}
        for c in poll.communities
    ]
    poll_dict['communities'] = communities
    
    return poll_dict
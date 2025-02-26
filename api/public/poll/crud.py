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
from api.public.poll.models import PollComment
from api.utils.generic_models import PollCommunityLink
from api.public.country.models import Country
from api.public.region.models import Region

def get_all_polls(db: Session, scope: str | None = None, current_user_id: int | None = None):
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

    # Obtener el conteo de comentarios por encuesta
    comments_count = db.exec(
        select(
            PollComment.poll_id,
            func.count(PollComment.id).label('comments_count')
        ).group_by(
            PollComment.poll_id
        )
    ).all()
    
    comments_dict = {
        comment.poll_id: comment.comments_count 
        for comment in comments_count
    }

    # Obtener los votos del usuario actual si está autenticado
    user_votes = {}
    if current_user_id:
        user_votes_query = select(PollVote).where(
            PollVote.user_id == current_user_id
        )
        user_votes_result = db.exec(user_votes_query).all()
        for vote in user_votes_result:
            if vote.poll_id not in user_votes:
                user_votes[vote.poll_id] = set()
            user_votes[vote.poll_id].add(vote.option_id)

    # Consulta principal para obtener encuestas, opciones y usuarios
    query = select(Poll, PollOption, User).join(PollOption).join(User, Poll.creator_id == User.id)
    
    if scope:
        query = query.where(Poll.scope == scope)
    
    results = db.exec(query).all()
    
    polls_dict = {}
    for poll, option, user in results:
        if poll.id not in polls_dict:
            poll_dict = poll.dict()
            if not poll.is_anonymous:
                poll_dict['creator_username'] = user.username
                del poll_dict['creator_id']
            else:
                del poll_dict['creator_id']
            
            poll_dict['reactions'] = reactions_dict.get(poll.id, {'LIKE': 0, 'DISLIKE': 0})
            poll_dict['comments_count'] = comments_dict.get(poll.id, 0)
            
            # Añadir países si el scope es INTERNATIONAL
            if poll.scope == "INTERNATIONAL":
                # Obtener los países a través de las comunidades
                countries = db.exec(
                    select(Country.cca2)
                    .join(Community, Community.id == Country.community_id)
                    .join(PollCommunityLink)
                    .where(PollCommunityLink.poll_id == poll.id)
                    .distinct()
                ).all()
                # Como countries ya contiene directamente los strings cca2
                poll_dict['countries'] = [country for country in countries if country]
            
            polls_dict[poll.id] = poll_dict
            polls_dict[poll.id]['options'] = []

        option_dict = option.dict()
        option_dict['voted'] = False
        if current_user_id and poll.id in user_votes:
            option_dict['voted'] = option.id in user_votes[poll.id]
        
        polls_dict[poll.id]['options'].append(option_dict)
    
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
        **poll_data.dict(exclude={'options', 'community_ids', 'country_codes', 'country_code', 'region_id'}),
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
    
    # Asociar las comunidades con la encuesta según el scope
    if poll_data.scope == "INTERNATIONAL" and poll_data.country_codes:
        # Buscar las comunidades asociadas a los códigos de país
        communities = db.exec(
            select(Community)
            .join(Country, Country.community_id == Community.id)
            .where(Country.cca2.in_(poll_data.country_codes))
        ).all()
        
        if not communities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontraron comunidades para los códigos de país proporcionados"
            )
            
        db_poll.communities.extend(communities)
    elif poll_data.scope == "NATIONAL" and poll_data.country_code:
        # Buscar la comunidad asociada al código de país nacional
        country = db.exec(
            select(Country)
            .where(Country.cca2 == poll_data.country_code)
        ).first()
        
        if not country or not country.community_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se encontró una comunidad para el país {poll_data.country_code}"
            )
            
        community = db.get(Community, country.community_id)
        if community:
            db_poll.communities.append(community)
    elif poll_data.scope == "REGIONAL" and poll_data.region_id:
        # Buscar la comunidad asociada a la región
        region = db.get(Region, poll_data.region_id)
        if not region or not region.community_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se encontró una comunidad para la región con ID {poll_data.region_id}"
            )
            
        community = db.get(Community, region.community_id)
        if community:
            db_poll.communities.append(community)
    elif poll_data.scope == "SUBREGIONAL" and poll_data.subregion_id:
        # Buscar la comunidad asociada a la subdivisión nacional
        from api.public.subregion.models import Subregion
        
        subregion = db.get(Subregion, poll_data.subregion_id)
        if not subregion or not subregion.community_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se encontró una comunidad para la subdivisión nacional con ID {poll_data.subregion_id}"
            )
            
        community = db.get(Community, subregion.community_id)
        if community:
            db_poll.communities.append(community)
    elif poll_data.community_ids:
        # Para otros scopes, usar community_ids directamente
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

def get_country_polls(db: Session, country_code: str, scope: str | None = None, current_user_id: int | None = None):
    """
    Obtiene todas las encuestas asociadas a un país específico.
    Incluye:
    - Encuestas nacionales del país (scope = NATIONAL)
    - Encuestas internacionales que incluyen al país (scope = INTERNATIONAL)
    - Encuestas subnacionales del país (scope = REGIONAL)
    Permite filtrar por scope específico
    """
    # Verificar que el país existe
    country = db.exec(
        select(Country).where(Country.cca2 == country_code)
    ).first()
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"País con código {country_code} no encontrado"
        )

    # Construir la consulta base para obtener encuestas
    query = (
        select(Poll, PollOption, User)
        .join(PollOption)
        .join(User, Poll.creator_id == User.id)
        .join(PollCommunityLink, Poll.id == PollCommunityLink.poll_id)
        .join(Community, PollCommunityLink.community_id == Community.id)
        .join(Country, Country.community_id == Community.id)
        .where(Country.cca2 == country_code)
    )

    # Aplicar filtro por scope si se especifica
    if scope:
        query = query.where(Poll.scope == scope)
    else:
        # Si no hay scope específico, mostrar todos los tipos de encuestas relevantes
        query = query.where(
            (Poll.scope == "NATIONAL") | 
            (Poll.scope == "INTERNATIONAL") |
            (Poll.scope == "REGIONAL")
        )

    query = query.distinct()

    # Obtener las encuestas
    results = db.exec(query).all()

    # Obtener conteo de reacciones
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

    # Crear diccionario de reacciones
    reactions_dict = {}
    for reaction in reactions_count:
        if reaction.poll_id not in reactions_dict:
            reactions_dict[reaction.poll_id] = {'LIKE': 0, 'DISLIKE': 0}
        reactions_dict[reaction.poll_id][reaction.reaction] = reaction.count

    # Obtener conteo de comentarios
    comments_count = db.exec(
        select(
            PollComment.poll_id,
            func.count(PollComment.id).label('comments_count')
        ).group_by(
            PollComment.poll_id
        )
    ).all()
    
    comments_dict = {
        comment.poll_id: comment.comments_count 
        for comment in comments_count
    }

    # Obtener votos del usuario actual si está autenticado
    user_votes = {}
    if current_user_id:
        user_votes_query = select(PollVote).where(
            PollVote.user_id == current_user_id
        )
        user_votes_result = db.exec(user_votes_query).all()
        for vote in user_votes_result:
            if vote.poll_id not in user_votes:
                user_votes[vote.poll_id] = set()
            user_votes[vote.poll_id].add(vote.option_id)

    # Procesar resultados
    polls_dict = {}
    for poll, option, user in results:
        if poll.id not in polls_dict:
            poll_dict = poll.dict()
            if not poll.is_anonymous:
                poll_dict['creator_username'] = user.username
                del poll_dict['creator_id']
            else:
                del poll_dict['creator_id']
            
            poll_dict['reactions'] = reactions_dict.get(poll.id, {'LIKE': 0, 'DISLIKE': 0})
            poll_dict['comments_count'] = comments_dict.get(poll.id, 0)
            
            # Añadir países si el scope es INTERNATIONAL
            if poll.scope == "INTERNATIONAL":
                countries = db.exec(
                    select(Country.cca2)
                    .join(Community, Community.id == Country.community_id)
                    .join(PollCommunityLink)
                    .where(PollCommunityLink.poll_id == poll.id)
                    .distinct()
                ).all()
                poll_dict['countries'] = [country for country in countries if country]
            
            polls_dict[poll.id] = poll_dict
            polls_dict[poll.id]['options'] = []

        option_dict = option.dict()
        option_dict['voted'] = False
        if current_user_id and poll.id in user_votes:
            option_dict['voted'] = option.id in user_votes[poll.id]
        
        polls_dict[poll.id]['options'].append(option_dict)
    
    return list(polls_dict.values())

def get_regional_polls(
    db: Session,
    region_id: int,
    scope: str | None = None,
    current_user_id: int | None = None
):
    """
    Obtener todas las encuestas asociadas a una región específica.
    """
    # Primero obtener la comunidad asociada a la región
    region_community = db.exec(
        select(Community)
        .join(Region, Community.id == Region.community_id)
        .where(Region.id == region_id)
    ).first()

    if not region_community:
        return []

    # Construir la consulta para obtener las encuestas
    query = (
        select(Poll)
        .distinct()
        .join(PollCommunityLink)
        .where(
            PollCommunityLink.community_id == region_community.id,
            Poll.status == PollStatus.PUBLISHED
        )
    )

    if scope:
        query = query.where(Poll.scope == scope)

    # Ordenar por fecha de creación, más recientes primero
    query = query.order_by(Poll.created_at.desc())

    polls = db.exec(query).all()
    
    # Enriquecer cada encuesta con información adicional
    return [
        enrich_poll(db, poll, current_user_id)
        for poll in polls
    ]

def enrich_poll(db: Session, poll: Poll, current_user_id: int | None = None) -> dict:
    """
    Enriquece una encuesta con información adicional:
    - Opciones y votos
    - Reacciones
    - Información del creador
    - Conteo de comentarios
    - Estado de votación del usuario actual
    """
    # Obtener el creador
    creator = db.get(User, poll.creator_id)
    
    # Obtener las opciones
    options = db.exec(
        select(PollOption)
        .where(PollOption.poll_id == poll.id)
    ).all()

    # Obtener reacciones
    reactions = db.exec(
        select(
            PollReaction.reaction,
            func.count(PollReaction.id).label('count')
        )
        .where(PollReaction.poll_id == poll.id)
        .group_by(PollReaction.reaction)
    ).all()
    
    reactions_dict = {'LIKE': 0, 'DISLIKE': 0}
    for reaction in reactions:
        reactions_dict[reaction.reaction] = reaction.count

    # Obtener conteo de comentarios
    comments_count = db.exec(
        select(func.count(PollComment.id))
        .where(PollComment.poll_id == poll.id)
    ).first()

    # Obtener votos del usuario actual si está autenticado
    user_votes = set()
    if current_user_id:
        votes = db.exec(
            select(PollVote.option_id)
            .where(
                PollVote.poll_id == poll.id,
                PollVote.user_id == current_user_id
            )
        ).all()
        user_votes = {vote for vote in votes}

    # Construir el diccionario de la encuesta
    poll_dict = poll.dict()
    
    # Agregar username del creador si la encuesta no es anónima
    if not poll.is_anonymous and creator:
        poll_dict['creator_username'] = creator.username
    del poll_dict['creator_id']

    # Agregar opciones con estado de votación
    poll_dict['options'] = [
        {
            **option.dict(),
            'voted': option.id in user_votes if current_user_id else False
        }
        for option in options
    ]

    # Agregar reacciones y comentarios
    poll_dict['reactions'] = reactions_dict
    poll_dict['comments_count'] = comments_count or 0

    return poll_dict
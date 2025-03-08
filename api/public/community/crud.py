from fastapi import HTTPException, status
from sqlmodel import Session, select
from typing import Optional
from api.public.community.models import Community
from api.public.user.models import UserCommunityLink
from api.public.user.models import User
from api.public.community.models import CommunityRequest
from datetime import datetime

def get_community(community_id: int, db: Session, check_membership: bool = False, current_user: Optional[User] = None):
    """
    Obtiene una comunidad por su ID.
    
    Args:
        community_id: ID de la comunidad a obtener
        db: Sesión de base de datos
        check_membership: Si es True, verifica que el usuario actual sea miembro
        current_user: Usuario actual (opcional)
        
    Returns:
        La comunidad si existe y el usuario tiene acceso, None en caso contrario
    """
    community = db.get(Community, community_id)
    
    if not community:
        return None
        
    # Solo verificar membresía si se solicita explícitamente
    if check_membership and current_user:
        # Verificar si el usuario es miembro de la comunidad
        is_member = db.exec(
            select(UserCommunityLink).where(
                UserCommunityLink.user_id == current_user.id,
                UserCommunityLink.community_id == community_id
            )
        ).first() is not None
        
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No eres miembro de esta comunidad"
            )
    
    return community

def get_community_by_id(session: Session, community_id: int) -> Optional[Community]:
    """
    Obtiene una comunidad por su ID
    
    Args:
        session: Sesión de base de datos
        community_id: ID de la comunidad a buscar
        
    Returns:
        Objeto Community si se encuentra, None en caso contrario
    """
    return session.get(Community, community_id)

def get_communities(session: Session, parent_id: Optional[int] = None, 
                   level: Optional[str] = None, skip: int = 0, 
                   limit: int = 100) -> list[Community]:
    """
    Obtiene una lista de comunidades, opcionalmente filtrada por comunidad padre o nivel
    
    Args:
        session: Sesión de base de datos
        parent_id: ID opcional de la comunidad padre para filtrar
        level: Nivel opcional de comunidad para filtrar
        skip: Número de registros a saltar
        limit: Número máximo de registros a devolver
        
    Returns:
        Lista de objetos Community
    """
    query = select(Community)
    
    if parent_id is not None:
        query = query.where(Community.parent_id == parent_id)
    
    if level:
        query = query.where(Community.level == level)
    
    return session.exec(query.offset(skip).limit(limit)).all()

def create_community(session: Session, community_data: dict) -> Community:
    """
    Crea una nueva comunidad
    
    Args:
        session: Sesión de base de datos
        community_data: Diccionario con los datos de la comunidad
        
    Returns:
        Objeto Community creado
    """
    community = Community(**community_data)
    session.add(community)
    session.commit()
    session.refresh(community)
    return community

def update_community(session: Session, community_id: int, 
                    community_data: dict) -> Optional[Community]:
    """
    Actualiza una comunidad existente
    
    Args:
        session: Sesión de base de datos
        community_id: ID de la comunidad a actualizar
        community_data: Diccionario con los datos a actualizar
        
    Returns:
        Objeto Community actualizado, None si no se encuentra
    """
    community = get_community_by_id(session, community_id)
    if not community:
        return None
        
    for key, value in community_data.items():
        setattr(community, key, value)
        
    session.commit()
    session.refresh(community)
    return community

def delete_community(session: Session, community_id: int) -> bool:
    """
    Elimina una comunidad
    
    Args:
        session: Sesión de base de datos
        community_id: ID de la comunidad a eliminar
        
    Returns:
        True si se eliminó correctamente, False si no se encontró
    """
    community = get_community_by_id(session, community_id)
    if not community:
        return False
        
    session.delete(community)
    session.commit()
    return True

def create_community_request(db: Session, request_data: dict):
    """
    Crea una nueva solicitud de comunidad en la base de datos
    """
    community_request = CommunityRequest(
        country=request_data["country"],
        region=request_data["region"],
        city=request_data["city"],
        email=request_data["email"]
    )
    db.add(community_request)
    db.commit()
    db.refresh(community_request)
    return community_request

def get_community_requests(db: Session, skip: int = 0, limit: int = 100, status: str = None):
    """
    Obtiene todas las solicitudes de comunidad con filtrado opcional por estado
    """
    query = db.query(CommunityRequest)
    if status:
        query = query.filter(CommunityRequest.status == status)
    return query.offset(skip).limit(limit).all()

def update_community_request_status(db: Session, request_id: int, status: str):
    """
    Actualiza el estado de una solicitud de comunidad
    """
    community_request = db.query(CommunityRequest).filter(CommunityRequest.id == request_id).first()
    if community_request:
        community_request.status = status
        community_request.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(community_request)
    return community_request
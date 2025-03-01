from fastapi import HTTPException, status
from sqlmodel import Session, select
from typing import Optional
from api.public.community.models import Community

def get_community(community_id: int, db: Session) -> Community:
    community = db.get(Community, community_id)
    if not community:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
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
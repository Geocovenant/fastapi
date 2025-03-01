from sqlmodel import Session, select
from typing import Optional
from api.public.subregion.models import Subregion

def get_subregion_by_id(session: Session, subregion_id: int) -> Optional[Subregion]:
    """
    Obtiene una subregión por su ID
    
    Args:
        session: Sesión de base de datos
        subregion_id: ID de la subregión a buscar
        
    Returns:
        Objeto Subregion si se encuentra, None en caso contrario
    """
    return session.get(Subregion, subregion_id)

def get_subregions(session: Session, region_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> list[Subregion]:
    """
    Obtiene una lista de subregiones, opcionalmente filtrada por región
    
    Args:
        session: Sesión de base de datos
        region_id: ID opcional de la región para filtrar
        skip: Número de registros a saltar
        limit: Número máximo de registros a devolver
        
    Returns:
        Lista de objetos Subregion
    """
    query = select(Subregion)
    if region_id:
        query = query.where(Subregion.region_id == region_id)
    return session.exec(query.offset(skip).limit(limit)).all()

def create_subregion(session: Session, subregion_data: dict) -> Subregion:
    """
    Crea una nueva subregión
    
    Args:
        session: Sesión de base de datos
        subregion_data: Diccionario con los datos de la subregión
        
    Returns:
        Objeto Subregion creado
    """
    subregion = Subregion(**subregion_data)
    session.add(subregion)
    session.commit()
    session.refresh(subregion)
    return subregion 
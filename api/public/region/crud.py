from sqlmodel import Session, select
from typing import Optional
from api.public.region.models import Region

def get_region_by_id(session: Session, region_id: int) -> Optional[Region]:
    """
    Obtiene una región por su ID
    
    Args:
        session: Sesión de base de datos
        region_id: ID de la región a buscar
        
    Returns:
        Objeto Region si se encuentra, None en caso contrario
    """
    return session.get(Region, region_id)

def get_regions(session: Session, skip: int = 0, limit: int = 100) -> list[Region]:
    """
    Obtiene una lista de regiones con paginación
    
    Args:
        session: Sesión de base de datos
        skip: Número de registros a saltar
        limit: Número máximo de registros a devolver
        
    Returns:
        Lista de objetos Region
    """
    return session.exec(select(Region).offset(skip).limit(limit)).all()

def create_region(session: Session, region_data: dict) -> Region:
    """
    Crea una nueva región
    
    Args:
        session: Sesión de base de datos
        region_data: Diccionario con los datos de la región
        
    Returns:
        Objeto Region creado
    """
    region = Region(**region_data)
    session.add(region)
    session.commit()
    session.refresh(region)
    return region 
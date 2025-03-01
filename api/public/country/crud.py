from sqlmodel import Session, select
from typing import Optional
from api.public.country.models import Country

def get_all_countries(session: Session) -> list[Country]:
    statement = select(Country)
    results = session.exec(statement).all()
    return results

def get_country_by_name(session: Session, country_name: str) -> Country:
    statement = select(Country).where(Country.name == country_name)
    result = session.exec(statement).first()
    return result

def get_country_by_code(session: Session, code: str) -> Optional[Country]:
    """
    Obtiene un país por su código CCA2
    
    Args:
        session: Sesión de base de datos
        code: Código CCA2 del país (ISO 3166-1 alpha-2)
        
    Returns:
        Objeto Country si se encuentra, None en caso contrario
    """
    statement = select(Country).where(Country.cca2 == code)
    result = session.exec(statement).first()
    return result
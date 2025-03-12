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
    Gets a country by its CCA2 code
    
    Args:
        session: Database session
        code: CCA2 code of the country (ISO 3166-1 alpha-2)
        
    Returns:
        Country object if found, None otherwise
    """
    statement = select(Country).where(Country.cca2 == code)
    result = session.exec(statement).first()
    return result
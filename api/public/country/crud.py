from sqlmodel import Session, select
from api.public.country.models import Country

def get_all_countries(session: Session) -> list[Country]:
    statement = select(Country)
    results = session.exec(statement).all()
    return results

def get_country_by_name(session: Session, country_name: str) -> Country:
    statement = select(Country).where(Country.name == country_name)
    result = session.exec(statement).first()
    return result
from sqlmodel import create_engine, SQLModel, Session
from api.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True, pool_size=20, max_overflow=10)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
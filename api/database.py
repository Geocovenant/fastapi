from sqlmodel import create_engine, SQLModel, Session
from api.config import settings

# Creation of the engine with improved pool configuration
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Check connections before using them
    echo=settings.ENV == "development"  # Show SQL only in development
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# We maintain the original function name for compatibility
def get_session():
    # We implement the try/finally pattern to ensure the session is closed
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
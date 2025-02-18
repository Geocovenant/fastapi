from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from api.public.country.models import Country

class Continent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=20, unique=True, index=True)

    # Relationships
    countries: list["Country"] = Relationship(back_populates="continent")
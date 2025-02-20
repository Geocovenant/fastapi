from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from api.public.community.models import Community

if TYPE_CHECKING:
    from api.public.country.models import Country

class Continent(SQLModel, table=True):
    __tablename__ = "continent"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=20, unique=True, index=True)
    community_id: int = Field(foreign_key="community.id")

    # Relationships
    community: Community = Relationship(back_populates="continent")
    countries: list["Country"] = Relationship(
        back_populates="continent",
        sa_relationship_kwargs={
            'primaryjoin': 'Continent.id==Country.continent_id'
        }
    )
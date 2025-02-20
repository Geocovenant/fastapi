from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from api.public.community.models import Community

class SubnationDivision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    area: Optional[float] = Field(default=None, description="Area in square kilometers")
    population: Optional[int] = Field(default=None, description="Population")
    borders: Optional[str] = Field(default=None, description="List of bordering countries")
    community_id: int = Field(foreign_key="community.id")
    subnation_id: Optional[int] = Field(default=None, foreign_key="subnation.id")

    # Relationships
    community: Community = Relationship(back_populates="subnation_division")
    subnation: Optional["Subnation"] = Relationship(back_populates="subnation_divisions")
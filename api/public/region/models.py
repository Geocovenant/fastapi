from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from api.public.subregion.models import Subregion
from api.public.community.models import Community

class Region(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    area: Optional[float] = Field(default=None, description="Area in square kilometers")
    population: Optional[int] = Field(default=None, description="Population")
    borders: Optional[str] = Field(default=None, description="List of bordering countries")
    capital: Optional[str] = Field(default=None, description="Capital city")
    flag: Optional[str] = Field(default=None, description="Emoji flag")
    iso_code: Optional[str] = Field(default=None, description="ISO 3166-2 code")
    timezone: Optional[str] = Field(default=None, description="Primary time zone")
    famous_landmark: Optional[str] = Field(default=None, description="Famous landmark")
    country_cca2: Optional[str] = Field(default=None, description="Country ISO 3166-1 alpha-2 code")
    community_id: int = Field(foreign_key="community.id")
    country_id: int = Field(foreign_key="country.id")

    # Relationships
    community: Community = Relationship(back_populates="region")
    country: "Country" = Relationship(back_populates="regions")
    subregions: list["Subregion"] = Relationship(back_populates="region")

from api.public.country.models import Country
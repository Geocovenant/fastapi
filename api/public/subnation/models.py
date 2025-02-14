from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Subnation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    area: Optional[float] = Field(default=None, description="Area in square kilometers")
    population: Optional[int] = Field(default=None, description="Population")
    borders: Optional[str] = Field(default=None, description="List of bordering countries")
    capital: Optional[str] = Field(default=None, description="Capital city")
    flag: Optional[str] = Field(default=None, description="Emoji flag")
    iso_code: Optional[str] = Field(default=None, description="ISO 3166-2 code")
    timezone: Optional[str] = Field(default=None, description="Primary time zone")
    famous_landmark: Optional[str] = Field(default=None, description="Famous landmark")

    country_id: Optional[int] = Field(default=None, foreign_key="country.id")

    # Relationships
    country: Optional["Country"] = Relationship(back_populates="subnations")
    subnation_divisions: list["SubnationDivision"] = Relationship(back_populates="subnation")
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from api.public.continent.models import Continent
from api.public.community.models import Community

class Country(SQLModel, table=True):
    __tablename__ = "country"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    area: Optional[float] = Field(default=None, description="Area in square kilometers")
    borders: Optional[str] = Field(default=None, description="List of bordering countries")
    capital_latlng: Optional[str] = Field(default=None, description="Latitude and longitude of the capital")
    capital: Optional[str] = Field(default=None, description="Capital city")
    cca2: str = Field(max_length=2, description="ISO 3166-1 alpha-2 code")
    cca3: Optional[str] = Field(default=None, description="ISO 3166-1 alpha-3 code")
    coat_of_arms_svg: Optional[str] = Field(default=None, description="URL to the coat of arms image")
    currency_code: Optional[str] = Field(default=None, description="ISO 4217 currency code")
    currency_name: Optional[str] = Field(default=None, description="Currency name")
    flag: Optional[str] = Field(default=None, description="Emoji flag")
    google_maps_link: Optional[str] = Field(default=None, description="Google Maps link")
    idd_root: Optional[str] = Field(default=None, description="International Direct Dialing root")
    idd_suffixes: Optional[str] = Field(default=None, description="International Direct Dialing suffixes")
    landlocked: Optional[bool] = Field(default=None, description="Landlocked status")
    languages: Optional[str] = Field(default=None, description="List of official languages")
    native_name: Optional[str] = Field(default=None, description="Native name")
    numeric_code: Optional[str] = Field(default=None, description="ISO 3166-1 numeric code")
    openstreetmap_link: Optional[str] = Field(default=None, description="OpenStreetMap link")
    population: Optional[int] = Field(default=None, description="Population")
    region: Optional[str] = Field(default=None, description="Region")
    status: Optional[str] = Field(default=None, description="Official assignment status")
    subregion: Optional[str] = Field(default=None, description="Subregion")
    timezone: Optional[str] = Field(default=None, description="Primary time zone")
    administrative_division_type: Optional[str] = Field(default=None, description="Name for administrative divisions (e.g. States, Provinces, Departments)")
    community_id: int = Field(foreign_key="community.id")
    continent_id: Optional[int] = Field(default=None, foreign_key="continent.id")

    # Relationships
    community: Community = Relationship(back_populates="country")
    continent: Optional[Continent] = Relationship(back_populates="countries")
    regions: List["Region"] = Relationship(back_populates="country")

from api.public.region.models import Region
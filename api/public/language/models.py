from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List

class Language(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=10, unique=True, index=True)  # ISO code (e.g., "es", "en")
    name: str = Field(max_length=50, unique=True, index=True)
    
    # Relationship
    countries: List["Country"] = Relationship(back_populates="languages", link_model="CountryLanguageLink")

class CountryLanguageLink(SQLModel, table=True):
    country_id: int = Field(foreign_key="country.id", primary_key=True)
    language_id: int = Field(foreign_key="language.id", primary_key=True)
    is_official: bool = Field(default=False)
    
    # Relationships
    country: "Country" = Relationship(back_populates="language_links")
    language: Language = Relationship(back_populates="country_links") 
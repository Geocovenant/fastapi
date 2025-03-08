from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON
from api.utils.generic_models import UserCommunityLink, PollCommunityLink, DebateCommunityLink, ProjectCommunityLink

class CommunityLevel(str, Enum):
    GLOBAL = "GLOBAL"
    INTERNATIONAL = "INTERNATIONAL"
    CONTINENT = "CONTINENT"
    NATIONAL = "NATIONAL"
    REGIONAL = "REGIONAL"
    SUBREGIONAL = "SUBREGIONAL"
    LOCAL = "LOCAL"
    CUSTOM = "CUSTOM"

class CommunityBase(SQLModel):
    name: str = Field(max_length=100, index=True)
    description: str = Field(default=None, max_length=500)
    level: CommunityLevel = Field(default=CommunityLevel.CUSTOM, index=True)
    geo_data: Optional[str] = Field(default=None, sa_column=Column(JSON))
    parent_id: Optional[int] = Field(default=None, foreign_key="community.id")

class Community(CommunityBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    members: list["User"] = Relationship(back_populates="communities", link_model=UserCommunityLink)
    parent: Optional["Community"] = Relationship(sa_relationship_kwargs={"remote_side": "Community.id"}, back_populates="children")
    children: list["Community"] = Relationship(back_populates="parent")
    polls: list["Poll"] = Relationship(back_populates="communities", link_model=PollCommunityLink)
    debates: list["Debate"] = Relationship(back_populates="communities", link_model=DebateCommunityLink)
    points_of_view: list["PointOfView"] = Relationship(back_populates="community")
    continent: "Continent" = Relationship(back_populates="community")
    country: "Country" = Relationship(back_populates="community")
    region: "Region" = Relationship(back_populates="community")
    subregion: "Subregion" = Relationship(back_populates="community")
    locality: "Locality" = Relationship(back_populates="community")
    projects: list["Project"] = Relationship(back_populates="communities", link_model=ProjectCommunityLink)

    def get_translated(self, language_code, field):
        """Obtiene un campo traducido si existe, o el valor por defecto"""
        for translation in self.translations:
            if translation.language_code == language_code:
                return getattr(translation, field)
        return getattr(self, field)  # Valor por defecto

class CommunityRead(CommunityBase):
    id: int

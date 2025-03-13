from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON
from api.utils.generic_models import UserCommunityLink, PollCommunityLink, DebateCommunityLink, ProjectCommunityLink, IssueCommunityLink
import datetime

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
    issues: list["Issue"] = Relationship(back_populates="communities", link_model=IssueCommunityLink)

    def get_translated(self, language_code, field):
        """Gets a translated field if it exists, or the default value"""
        for translation in self.translations:
            if translation.language_code == language_code:
                return getattr(translation, field)
        return getattr(self, field)  # Default value

class CommunityRead(CommunityBase):
    id: int
    parent_id: Optional[int] = None
    region_id: Optional[int] = None  # New optional field

class CommunityRequest(SQLModel, table=True):
    __tablename__ = "community_requests"

    id: int = Field(primary_key=True, index=True)
    country: str = Field(nullable=False)
    region: str = Field(nullable=False)
    city: str = Field(nullable=False)
    email: str = Field(nullable=False)
    status: str = Field(default="pending")  # pending, approved, rejected
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<CommunityRequest(id={self.id}, country='{self.country}', region='{self.region}', city='{self.city}')>"

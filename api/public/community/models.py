from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON
from api.utils.generic_models import UserCommunityLink

class CommunityLevel(str, Enum):
    GLOBAL = "GLOBAL"
    INTERNATIONAL = "INTERNATIONAL"
    NATIONAL = "NATIONAL"
    SUBNATIONAL = "SUBNATIONAL"
    LOCAL = "LOCAL"
    CUSTOM = "CUSTOM"

class CommunityBase(SQLModel):
    name: str = Field(max_length=100, unique=True, index=True, regex=r"^[a-zA-Z0-9_]+$")
    description: str = Field(default=None, max_length=500)
    level: CommunityLevel = Field(default=CommunityLevel.CUSTOM)
    geo_data: Optional[str] = Field(default=None, sa_column=Column(JSON))

    parent_id: Optional[int] = Field(default=None, foreign_key="community.id")

class Community(CommunityBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Relationships
    members: list["User"] = Relationship(back_populates="communities", link_model=UserCommunityLink)
    parent: Optional["Community"] = Relationship(sa_relationship_kwargs={"remote_side": "Community.id"}, back_populates="children")
    children: list["Community"] = Relationship(back_populates="parent")

class CommunityRead(CommunityBase):
    id: int
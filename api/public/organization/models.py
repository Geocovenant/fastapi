from enum import Enum
from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

# Enums
class OrganizationLevel(str, Enum):
    MUNICIPAL = "MUNICIPAL"
    PROVINCIAL = "PROVINCIAL"
    REGIONAL = "REGIONAL"
    NATIONAL = "NATIONAL"

# Model for organizations
class Organization(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, index=True)
    level: OrganizationLevel = Field(index=True)
    description: Optional[str] = Field(default=None, max_length=1000)
    parent_id: Optional[int] = Field(default=None, foreign_key="organization.id")
    community_id: Optional[int] = Field(default=None, foreign_key="community.id")
    region_id: Optional[int] = Field(default=None, foreign_key="region.id")
    subregion_id: Optional[int] = Field(default=None, foreign_key="subregion.id")
    locality_id: Optional[int] = Field(default=None, foreign_key="locality.id")
    contact_email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=50)
    website: Optional[str] = Field(default=None, max_length=200)
    
    # Relationships
    parent: Optional["Organization"] = Relationship(
        back_populates="children", 
        sa_relationship_kwargs={"remote_side": "Organization.id"}
    )
    children: list["Organization"] = Relationship(back_populates="parent")
    issues: list["Issue"] = Relationship(back_populates="organization")
    issue_updates: list["IssueUpdate"] = Relationship(back_populates="organization")

# Models for CRUD operations
class OrganizationBase(SQLModel):
    name: str = Field(max_length=200)
    level: OrganizationLevel
    description: Optional[str] = Field(default=None, max_length=1000)
    parent_id: Optional[int] = None
    community_id: Optional[int] = None
    region_id: Optional[int] = None
    subregion_id: Optional[int] = None
    locality_id: Optional[int] = None
    contact_email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=50)
    website: Optional[str] = Field(default=None, max_length=200)

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationRead(OrganizationBase):
    id: int 
from enum import Enum
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from api.public.tag.models import Tag
from api.utils.generic_models import ProjectCommunityLink

class ProjectStatus(str, Enum):
    DRAFT = "DRAFT"         # Project in draft
    OPEN = "OPEN"           # Project open for collaboration
    IN_PROGRESS = "IN_PROGRESS"  # Project in execution
    COMPLETED = "COMPLETED"  # Project finished
    CANCELLED = "CANCELLED"  # Project cancelled

class ResourceType(str, Enum):
    LABOR = "LABOR"         # Labor (work hours)
    MATERIAL = "MATERIAL"   # Physical materials
    ECONOMIC = "ECONOMIC"   # Economic resources (money)

class CommitmentType(str, Enum):
    TIME = "TIME"           # Time commitment
    MATERIAL = "MATERIAL"   # Material commitment
    ECONOMIC = "ECONOMIC"   # Economic commitment

class ProjectBase(SQLModel):
    title: str = Field(max_length=100, index=True, description="Project title")
    description: Optional[str] = Field(max_length=5000, nullable=True, description="Detailed description")
    status: ProjectStatus = Field(default=ProjectStatus.OPEN, description="Project status")
    goal_amount: Optional[float] = Field(default=None, description="Target amount for fundraising")
    current_amount: float = Field(default=0.0, description="Current amount raised")
    scope: str = Field(max_length=100, nullable=True, description="Scope: 'LOCAL', 'REGIONAL', etc.")

class Project(ProjectBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(max_length=100, index=True, unique=True, description="Unique readable identifier")
    creator_id: int = Field(foreign_key="users.id", description="Creator user ID")
    created_at: datetime = Field(default=datetime.utcnow, description="Creation date")
    updated_at: datetime = Field(default=datetime.utcnow, description="Last update date")
    views_count: int = Field(default=0, description="Number of project views")

    # Relationships
    creator: "User" = Relationship(back_populates="projects")
    steps: list["ProjectStep"] = Relationship(back_populates="project", cascade_delete=True)
    commitments: list["ProjectCommitment"] = Relationship(back_populates="project", cascade_delete=True)
    donations: list["ProjectDonation"] = Relationship(back_populates="project", cascade_delete=True)
    communities: list["Community"] = Relationship(back_populates="projects", link_model=ProjectCommunityLink)

class ProjectStep(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", description="Associated project ID")
    title: str = Field(max_length=100, description="Step title")
    description: Optional[str] = Field(max_length=1000, nullable=True, description="Step details")
    order: int = Field(default=0, description="Step order in the project")
    status: str = Field(default="PENDING", description="Status: PENDING, IN_PROGRESS, COMPLETED")

    # Relationships
    project: Project = Relationship(back_populates="steps")
    resources: list["ProjectResource"] = Relationship(back_populates="step", cascade_delete=True)

class ProjectResource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    step_id: int = Field(foreign_key="projectstep.id", description="Associated step ID")
    type: ResourceType = Field(description="Resource type: LABOR, MATERIAL, ECONOMIC")
    description: str = Field(max_length=200, description="Resource description")
    quantity: Optional[float] = Field(default=None, description="Required quantity")
    unit: Optional[str] = Field(default=None, max_length=50, description="Unit: hours, kg, etc.")

    # Relationships
    step: ProjectStep = Relationship(back_populates="resources")

class ProjectCommitment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", description="Associated project ID")
    user_id: int = Field(foreign_key="users.id", description="ID of the user making the commitment")
    type: CommitmentType = Field(description="Type: TIME, MATERIAL, ECONOMIC")
    description: str = Field(max_length=200, description="Commitment details")
    quantity: Optional[float] = Field(default=None, description="Offered quantity")
    unit: Optional[str] = Field(default=None, max_length=50, description="Unit: hours, units, etc.")
    fulfilled: bool = Field(default=False, description="Whether the commitment has been fulfilled")

    # Relationships
    project: Project = Relationship(back_populates="commitments")
    user: "User" = Relationship(back_populates="project_commitments")

class ProjectDonation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", description="Associated project ID")
    user_id: int = Field(foreign_key="users.id", description="Donor user ID")
    amount: float = Field(description="Donated amount")
    donated_at: datetime = Field(default=datetime.utcnow, description="Donation date")

    # Relationships
    project: Project = Relationship(back_populates="donations")
    user: "User" = Relationship(back_populates="project_donations")

# Models for Creation and Reading
class ProjectStepCreate(SQLModel):
    title: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    order: int = Field(default=0)
    status: str = Field(default="PENDING")
    resources: list["ProjectResourceCreate"] = Field(default=[])

class ProjectResourceCreate(SQLModel):
    type: ResourceType
    description: str = Field(max_length=200)
    quantity: Optional[float] = None
    unit: Optional[str] = Field(default=None, max_length=50)

class ProjectCommitmentCreate(SQLModel):
    type: CommitmentType
    description: str = Field(max_length=200)
    quantity: Optional[float] = None
    unit: Optional[str] = Field(default=None, max_length=50)

class ProjectDonationCreate(SQLModel):
    amount: float

class ProjectCreate(ProjectBase):
    steps: list[ProjectStepCreate] = Field(default=[])
    community_ids: list[int] = Field(default=[], description="Associated community IDs")
    country_codes: Optional[list[str]] = Field(default=None, description="List of CCA2 country codes for international projects")
    country_code: Optional[str] = Field(default=None, description="CCA2 country code for national projects")
    region_id: Optional[int] = Field(default=None, description="Region ID for regional projects")
    subregion_id: Optional[int] = Field(default=None, description="Subdivision ID for subregional projects")
    locality_id: Optional[int] = Field(default=None, description="Locality ID for local projects")

class CommunityMinimal(SQLModel):
    id: int
    name: str
    cca2: Optional[str] = None

class UserMinimal(SQLModel):
    id: int
    username: str
    image: Optional[str] = None

class ProjectResourceRead(SQLModel):
    id: int
    type: ResourceType
    description: str
    quantity: Optional[float]
    unit: Optional[str]

class ProjectStepRead(SQLModel):
    id: int
    title: str
    description: Optional[str]
    order: int
    status: str
    resources: list[ProjectResourceRead] = []

class ProjectCommitmentRead(SQLModel):
    id: int
    user: UserMinimal
    type: CommitmentType
    description: str
    quantity: Optional[float]
    unit: Optional[str]
    fulfilled: bool

class ProjectDonationRead(SQLModel):
    id: int
    user: UserMinimal
    amount: float
    donated_at: datetime

class ProjectRead(ProjectBase):
    id: int
    slug: str
    creator: UserMinimal
    created_at: datetime
    updated_at: datetime
    steps: list[ProjectStepRead] = []
    commitments: list[ProjectCommitmentRead] = []
    donations: list[ProjectDonationRead] = []
    communities: list[CommunityMinimal] = []

class ProjectUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[ProjectStatus] = None
    goal_amount: Optional[float] = None
    community_ids: Optional[list[int]] = None

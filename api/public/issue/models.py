from enum import Enum
from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy import JSON
from api.public.user.models import User
from api.public.organization.models import Organization, OrganizationRead
from api.public.tag.models import Tag
from api.public.community.models import Community
from api.utils.generic_models import IssueCommunityLink, IssueTagLink
from api.utils.shared_models import UserMinimal, CommunityMinimal

# Enums
class IssueStatus(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"

class IssueScope(str, Enum):
    GLOBAL = "GLOBAL"
    INTERNATIONAL = "INTERNATIONAL"
    NATIONAL = "NATIONAL"
    REGIONAL = "REGIONAL"
    SUBREGIONAL = "SUBREGIONAL"
    LOCAL = "LOCAL"

class IssuePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

# Main model for issue reports
class Issue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200, index=True)
    description: str = Field(max_length=5000)
    status: IssueStatus = Field(default=IssueStatus.OPEN, index=True)
    priority: IssuePriority = Field(default=IssuePriority.MEDIUM)
    scope: IssueScope = Field(default=IssueScope.LOCAL)
    location: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    slug: str = Field(max_length=250, unique=True, index=True)
    supports_count: int = Field(default=0)
    views_count: int = Field(default=0)
    creator_id: int = Field(foreign_key="users.id")
    organization_id: Optional[int] = Field(default=None, foreign_key="organization.id")
    is_anonymous: bool = Field(default=False)

    # Relationships
    creator: User = Relationship(back_populates="issues_created")
    organization: Optional[Organization] = Relationship(back_populates="issues")
    supports: list["IssueSupport"] = Relationship(back_populates="issue", cascade_delete=True)
    comments: list["IssueComment"] = Relationship(back_populates="issue", cascade_delete=True)
    updates: list["IssueUpdate"] = Relationship(back_populates="issue", cascade_delete=True)
    
    # Nuevas relaciones
    tags: list["Tag"] = Relationship(back_populates="issues", link_model=IssueTagLink)
    communities: list["Community"] = Relationship(back_populates="issues", link_model=IssueCommunityLink)
    images: list["IssueImage"] = Relationship(back_populates="issue", cascade_delete=True)

# Model for issue images
class IssueImage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    issue_id: int = Field(foreign_key="issue.id")
    url: str = Field(max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    issue: Issue = Relationship(back_populates="images")

# Model for community support
class IssueSupport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    issue_id: int = Field(foreign_key="issue.id")
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    issue: Issue = Relationship(back_populates="supports")
    user: User = Relationship(back_populates="issue_supports")

# Model for comments
class IssueComment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    issue_id: int = Field(foreign_key="issue.id")
    user_id: int = Field(foreign_key="users.id")
    content: str = Field(max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    issue: Issue = Relationship(back_populates="comments")
    user: User = Relationship(back_populates="issue_comments")

# Model for issue updates
class IssueUpdate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    issue_id: int = Field(foreign_key="issue.id")
    organization_id: int = Field(foreign_key="organization.id")
    user_id: int = Field(foreign_key="users.id")
    content: str = Field(max_length=1000)
    new_status: Optional[IssueStatus] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    issue: Issue = Relationship(back_populates="updates")
    organization: Organization = Relationship(back_populates="issue_updates")
    user: User = Relationship(back_populates="issue_updates")

# Models for CRUD operations
class IssueCategoryBase(SQLModel):
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)

class IssueCategoryCreate(IssueCategoryBase):
    pass

class IssueCategoryRead(IssueCategoryBase):
    id: int

class UserMinimal(SQLModel):
    id: int
    username: str
    image: Optional[str] = None

class IssueCommentBase(SQLModel):
    content: str = Field(max_length=1000)

class IssueCommentCreate(IssueCommentBase):
    pass

class IssueCommentRead(IssueCommentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: UserMinimal

class IssueUpdateBase(SQLModel):
    content: str = Field(max_length=1000)
    new_status: Optional[IssueStatus] = None

class IssueUpdateCreate(IssueUpdateBase):
    pass

class IssueUpdateRead(IssueUpdateBase):
    id: int
    created_at: datetime
    user: UserMinimal
    organization: OrganizationRead

class IssueBase(SQLModel):
    title: str = Field(max_length=200)
    description: str = Field(max_length=5000)
    priority: IssuePriority = Field(default=IssuePriority.MEDIUM)
    scope: IssueScope = Field(default=IssueScope.LOCAL)
    location: Optional[dict] = Field(default=None)
    organization_id: Optional[int] = Field(default=None)
    is_anonymous: bool = Field(default=False)

class IssueCreate(IssueBase):
    status: IssueStatus = Field(default=IssueStatus.OPEN)
    images: list[str] = Field(default=[])
    tags: list[str] = Field(default=[])
    community_ids: list[int] = Field(default=[])
    country_codes: Optional[list[str]] = Field(default=None, description="List of CCA2 country codes for international issues")
    country_code: Optional[str] = Field(default=None, description="CCA2 country code for national issues")
    region_id: Optional[int] = Field(default=None, description="Region ID for regional issues")
    subregion_id: Optional[int] = Field(default=None, description="Subregion ID for subregional issues")
    locality_id: Optional[int] = Field(default=None, description="Locality ID for local issues")

class IssueRead(IssueBase):
    id: int
    slug: str
    status: IssueStatus
    created_at: datetime
    updated_at: datetime
    supports_count: int
    views_count: int
    creator: Optional[UserMinimal] = None
    organization: Optional[OrganizationRead] = None
    images: list[str] = []
    communities: list[CommunityMinimal] = []
    tags: list[str] = []
    comments: list[IssueCommentRead] = []
    updates: list[IssueUpdateRead] = []
    user_supports: bool = False
    is_anonymous: bool = False

class PaginatedResponse(SQLModel):
    items: list
    total: int
    page: int
    size: int
    pages: int

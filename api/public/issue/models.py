from enum import Enum
from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from api.public.user.models import User
from api.public.organization.models import Organization, OrganizationRead, OrganizationLevel

# Enums
class IssueStatus(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"

# Model for issue categories
class IssueCategory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, index=True)
    description: Optional[str] = Field(default=None, max_length=500)
    
    # Relationships
    issues: list["Issue"] = Relationship(back_populates="category")

# Main model for issue reports
class Issue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200, index=True)
    description: str = Field(max_length=5000)
    status: IssueStatus = Field(default=IssueStatus.OPEN, index=True)
    location_description: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    slug: str = Field(max_length=250, unique=True, index=True)
    support_count: int = Field(default=0)
    community_id: Optional[int] = Field(default=None, foreign_key="community.id")
    region_id: Optional[int] = Field(default=None, foreign_key="region.id")
    subregion_id: Optional[int] = Field(default=None, foreign_key="subregion.id")
    locality_id: Optional[int] = Field(default=None, foreign_key="locality.id")
    creator_id: int = Field(foreign_key="users.id")
    category_id: int = Field(foreign_key="issuecategory.id")
    organization_id: int = Field(foreign_key="organization.id")
    
    # Relationships
    creator: User = Relationship(back_populates="issues_created")
    category: IssueCategory = Relationship(back_populates="issues")
    organization: Organization = Relationship(back_populates="issues")
    supports: list["IssueSupport"] = Relationship(back_populates="issue", cascade_delete=True)
    comments: list["IssueComment"] = Relationship(back_populates="issue", cascade_delete=True)
    updates: list["IssueUpdate"] = Relationship(back_populates="issue", cascade_delete=True)
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

class IssueBase(SQLModel):
    title: str = Field(max_length=200)
    description: str = Field(max_length=5000)
    location_description: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    community_id: Optional[int] = None
    region_id: Optional[int] = None
    subregion_id: Optional[int] = None
    locality_id: Optional[int] = None
    category_id: int
    organization_id: int

class IssueCreate(IssueBase):
    images: Optional[list[str]] = None

class IssueRead(IssueBase):
    id: int
    slug: str
    status: IssueStatus
    created_at: datetime
    updated_at: datetime
    support_count: int
    creator: Optional["UserMinimal"] = None
    category: Optional[IssueCategoryRead] = None
    organization: Optional[OrganizationRead] = None
    images: Optional[list[str]] = None

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

class PaginatedResponse(SQLModel):
    items: list
    total: int
    page: int
    size: int
    pages: int

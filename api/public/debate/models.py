from enum import Enum
from typing import Optional
from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy import JSON, BigInteger
from api.public.tag.models import Tag
from api.public.user.models import User
from api.public.community.models import Community
from api.utils.generic_models import DebateTagLink, DebateCommunityLink
from api.utils.shared_models import UserMinimal, CommunityMinimal
from pydantic import field_validator

class DebateType(str, Enum):
    GLOBAL = "GLOBAL"
    INTERNATIONAL = "INTERNATIONAL"
    NATIONAL = "NATIONAL"
    REGIONAL = "REGIONAL"
    SUBREGIONAL = "SUBREGIONAL"
    LOCAL = "LOCAL"

class DebateStatus(str, Enum):
    OPEN = "OPEN"
    PENDING = "PENDING"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"
    RESOLVED = "RESOLVED"

class LanguageCode(str, Enum):
    EN = "en"
    ES = "es"
    FR = "fr"

# Base model with common fields for Debate
class DebateBase(SQLModel):
    title: str = Field(index=True, min_length=5, max_length=100, description="Debate title")
    description: Optional[str] = Field(default=None, max_length=10000, description="Debate description")
    views_count: int = Field(default=0, ge=0, sa_column=Column(BigInteger), description="Number of views of the debate")
    images: list[str] = Field(default_factory=list, sa_column=Column(JSON), description="list of image URLs")
    language: LanguageCode = Field(default=LanguageCode.ES, description="Debate language code")
    public: bool = Field(default=True, description="Whether the debate is public or private")
    slug: str = Field(unique=True, index=True, description="Slug for the debate, generated from the title")
    status: DebateStatus = Field(default=DebateStatus.OPEN, description="Debate status")
    type: DebateType = Field(description="Debate type: GLOBAL, INTERNATIONAL, NATIONAL, REGIONAL, SUBREGIONAL, LOCAL")
    is_anonymous: bool = Field(default=False, description="Whether the debate creator is anonymous")

# Main Debate model, representing the debates table in the database
class Debate(DebateBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    creator_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Debate creation date", index=True)
    updated_at: Optional[datetime] = Field(default=None, description="Debate last update date")
    deleted_at: Optional[datetime] = Field(default=None, description="Debate deletion date")
    approved_by_id: Optional[int] = Field(default=None, foreign_key="users.id")
    rejected_by_id: Optional[int] = Field(default=None, foreign_key="users.id")
    approved_at: Optional[datetime] = Field(default=None)
    rejected_at: Optional[datetime] = Field(default=None)
    moderation_notes: Optional[str] = Field(default=None, description="Moderator notes")

    # Relationships
    creator: User = Relationship(
        back_populates="debates_created",
        sa_relationship_kwargs={"foreign_keys": "[Debate.creator_id]"}
    )
    approved_by: Optional[User] = Relationship(
        back_populates="debates_approved",
        sa_relationship_kwargs={"foreign_keys": "[Debate.approved_by_id]"}
    )
    rejected_by: Optional[User] = Relationship(
        back_populates="debates_rejected",
        sa_relationship_kwargs={"foreign_keys": "[Debate.rejected_by_id]"}
    )
    tags: list[Tag] = Relationship(back_populates="debates", link_model=DebateTagLink)
    communities: list["Community"] = Relationship(back_populates="debates", link_model=DebateCommunityLink)
    points_of_view: list["PointOfView"] = Relationship(back_populates="debate", cascade_delete=True)
    change_logs: list["DebateChangeLog"] = Relationship(back_populates="debate", cascade_delete=True)
    comments: list["Comment"] = Relationship(back_populates="debate", cascade_delete=True)

# Model for point of view in a debate
class PointOfView(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, description="Point of view name")
    debate_id: int = Field(foreign_key="debate.id")
    created_by_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    community_id: int = Field(foreign_key="community.id")
    
    # Relationships
    debate: Debate = Relationship(back_populates="points_of_view")
    created_by: User = Relationship()
    opinions: list["Opinion"] = Relationship(back_populates="point_of_view", cascade_delete=True)
    community: list[Community] = Relationship(back_populates="points_of_view")

# Model for opinions in a point of view
class Opinion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    point_of_view_id: int = Field(foreign_key="pointofview.id")
    user_id: int = Field(foreign_key="users.id")
    content: str = Field(max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    point_of_view: PointOfView = Relationship(back_populates="opinions")
    user: User = Relationship()
    votes: list["OpinionVote"] = Relationship(back_populates="opinion", cascade_delete=True)

# Model for votes on opinions
class OpinionVote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    opinion_id: int = Field(foreign_key="opinion.id")
    user_id: int = Field(foreign_key="users.id")
    value: int = Field(description="Vote value: 1 (positive) or -1 (negative)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    opinion: Opinion = Relationship(back_populates="votes")
    user: User = Relationship()

# Model for debate change logs
class DebateChangeLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    debate_id: int = Field(foreign_key="debate.id")
    changed_by_id: int = Field(foreign_key="users.id")
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    field_changed: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None

    # Relationships
    debate: Debate = Relationship(back_populates="change_logs")
    changed_by: User = Relationship()

# Models for creation, reading, and updating
class PointOfViewCreate(SQLModel):
    name: str = Field(max_length=100)
    community_ids: list[int] = Field(default=[])

class OpinionCreate(SQLModel):
    content: str
    community_id: Optional[int] = None
    country_cca2: Optional[str] = None
    region_id: Optional[int] = None

class OpinionVoteCreate(SQLModel):
    opinion_id: int
    value: int = Field(ge=-1, le=1)

class DebateCreate(SQLModel):
    title: str = Field(min_length=5, max_length=100)
    description: Optional[str] = Field(default=None, max_length=10000)
    type: DebateType
    community_ids: list[int] = Field(default=[])
    tags: list[str] = Field(default=[])
    images: list[str] = Field(default=[])
    language: LanguageCode = Field(default=LanguageCode.ES)
    public: bool = Field(default=True)
    is_anonymous: bool = Field(default=False)
    points_of_view: list[PointOfViewCreate] = Field(default=[])
    country_codes: Optional[list[str]] = Field(default=None, description="list of CCA2 country codes for international debates")
    country_code: Optional[str] = Field(default=None, description="CCA2 country code for national debates")
    region_id: Optional[int] = Field(default=None, description="Region ID for regional debates")
    subregion_id: Optional[int] = Field(default=None, description="Subregion ID for subregional debates")
    locality_id: Optional[int] = Field(default=None, description="Locality ID for local debates")

    @field_validator("community_ids")
    def validate_communities_by_type(cls, v, info):
        debate_type = info.data.get("type")
        
        if debate_type == DebateType.NATIONAL and not info.data.get("country_code"):
            raise ValueError("National debates require a country code (country_code)")
            
        return v

class OpinionRead(SQLModel):
    id: int
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: UserMinimal
    upvotes: int = 0
    downvotes: int = 0
    score: int = 0
    user_vote: Optional[int] = None

class PointOfViewRead(SQLModel):
    id: int
    name: str
    created_at: datetime
    created_by: UserMinimal
    community: CommunityMinimal
    opinions: list[OpinionRead] = []

class DebateRead(DebateBase):
    id: int
    creator: Optional[UserMinimal]
    created_at: datetime
    updated_at: Optional[datetime] = None
    communities: list[CommunityMinimal] = []
    tags: list[str] = []
    points_of_view: list[PointOfViewRead] = []
    is_anonymous: bool = False

class DebateUpdate(SQLModel):
    title: Optional[str] = Field(default=None, min_length=5, max_length=100)
    description: Optional[str] = Field(default=None, max_length=10000)
    status: Optional[DebateStatus] = None
    public: Optional[bool] = None
    tags: Optional[list[str]] = None
    images: Optional[list[str]] = None
    community_ids: Optional[list[int]] = None

class PaginatedDebateResponse(SQLModel):
    items: list[DebateRead]
    total: int
    page: int
    size: int
    pages: int

class CommentBase(SQLModel):
    content: str = Field(max_length=1000, description="Content of the comment")

class CommentCreate(CommentBase):
    pass

class CommentRead(CommentBase):
    id: int
    user: UserMinimal
    created_at: datetime
    updated_at: Optional[datetime] = None
    can_edit: bool = False

class Comment(CommentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    debate_id: int = Field(foreign_key="debate.id")
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    debate: "Debate" = Relationship(back_populates="comments")
    user: User = Relationship(back_populates="debate_comments") 
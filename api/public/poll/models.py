from enum import Enum
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional
from api.public.tag.models import Tag
from api.utils.generic_models import PollCommunityLink, PollTagLink

# Enums
class PollType(str, Enum):
    BINARY = "BINARY"
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    OPEN_CHOICE = "OPEN_CHOICE"  # New option that allows custom responses
    RANKING = "RANKING"  # New option to rank by preference order
    SCALE = "SCALE"  # New option for scale ratings

class PollStatus(str, Enum):
    DRAFT = "DRAFT"
    CLOSED = "CLOSED"
    PUBLISHED = "PUBLISHED"

class ReactionType(str, Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"

class PollBase(SQLModel):
    title: str = Field(max_length=100, index=True)
    description: Optional[str] = Field(max_length=5000, nullable=True)
    type: PollType = Field(default=PollType.BINARY)
    is_anonymous: bool = Field(default=True)
    ends_at: Optional[datetime] = Field(nullable=True)
    scope: str = Field(max_length=100, nullable=True, description="The scope of the poll, e.g. 'GLOBAL', 'INTERNATINAL', 'NATIONAL', etc.")

class Poll(PollBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(max_length=100, index=True, unique=True)
    creator_id: int = Field(foreign_key="users.id")
    status: PollStatus = Field(default=PollStatus.PUBLISHED)
    created_at: datetime = Field(default=datetime.utcnow)
    updated_at: datetime = Field(default=datetime.utcnow)
    views_count: int = Field(default=0)

    # Relationships
    communities: list["Community"] = Relationship(back_populates="polls", link_model=PollCommunityLink)
    tags: list[Tag] = Relationship(back_populates="polls", link_model=PollTagLink)
    creator: "User" = Relationship(back_populates="polls")
    options: list["PollOption"] = Relationship(back_populates="poll", cascade_delete=True)
    votes: list["PollVote"] = Relationship(back_populates="poll", cascade_delete=True)
    reactions: list["PollReaction"] = Relationship(back_populates="poll", cascade_delete=True)
    comments: list["PollComment"] = Relationship(back_populates="poll", cascade_delete=True)

class PollOption(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    poll_id: int = Field(foreign_key="poll.id")
    text: str = Field(max_length=150)
    votes: int = Field(default=0)
    is_custom_option: bool = Field(default=False)  # New field to identify if it's the "Other" option
    custom_responses: list["PollCustomResponse"] = Relationship(back_populates="option")  # New relationship

    # Relationships
    poll: Poll = Relationship(back_populates="options")
    votes_rel: list["PollVote"] = Relationship(back_populates="option")

class PollVote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    poll_id: int = Field(foreign_key="poll.id")
    option_id: int = Field(foreign_key="polloption.id")
    user_id: int = Field(foreign_key="users.id")

    # Relationships
    poll: Poll = Relationship(back_populates="votes")
    option: Optional[PollOption] = Relationship(back_populates="votes_rel")
    user: "User" = Relationship(back_populates="poll_votes")

class PollReaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    poll_id: int = Field(foreign_key="poll.id")
    user_id: int = Field(foreign_key="users.id")
    reaction: ReactionType = Field()
    reacted_at: datetime = Field(default=datetime.utcnow)

    # Relationships
    poll: Poll = Relationship(back_populates="reactions")
    user: "User" = Relationship(back_populates="poll_reactions")

class PollComment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    poll_id: int = Field(foreign_key="poll.id")
    user_id: int = Field(foreign_key="users.id")
    content: str = Field(max_length=500)
    created_at: datetime = Field(default=datetime.utcnow)
    updated_at: datetime = Field(default=datetime.utcnow)

    # Relationships
    poll: Poll = Relationship(back_populates="comments")
    user: "User" = Relationship(back_populates="poll_comments")

class PollOptionCreate(SQLModel):
    text: str = Field(max_length=150)
    is_custom_option: bool = Field(default=False)

class PollCreate(PollBase):
    options: list[PollOptionCreate]
    community_ids: list[int] = Field(default=[])
    country_codes: Optional[list[str]] = Field(default=None, description="List of CCA2 country codes for international polls")
    country_code: Optional[str] = Field(default=None, description="CCA2 country code for national polls")
    region_id: Optional[int] = Field(default=None, description="Region ID for regional polls")
    subregion_id: Optional[int] = Field(default=None, description="National subdivision ID for subnational polls")

class CommunityBase(SQLModel):
    id: int
    name: str
    description: Optional[str]

class PollReactionCount(SQLModel):
    LIKE: int = 0
    DISLIKE: int = 0

class PollOptionRead(SQLModel):
    id: int
    text: str
    votes: int
    voted: bool = False  # New field to indicate if the user voted for this option

class PollCommentCreate(SQLModel):
    content: str = Field(max_length=500)

class PollCommentUpdate(SQLModel):
    content: str = Field(max_length=500)

class UserMinimal(SQLModel):
    id: int
    username: str
    image: Optional[str] = None

class PollRead(PollBase):
    id: int
    slug: str
    creator: Optional[UserMinimal] = None
    status: PollStatus
    created_at: datetime
    updated_at: datetime
    options: list[PollOptionRead]
    communities: list[CommunityBase]
    reactions: PollReactionCount
    comments_count: int = 0
    countries: Optional[list[str]] = None
    user_reaction: Optional[ReactionType] = None
    user_voted_options: Optional[list[int]] = None  # New key for the IDs of voted options

class PollVoteCreate(SQLModel):
    option_ids: list[int] = Field(description="List of IDs of selected options")

class PollReactionCreate(SQLModel):
    reaction: ReactionType

# New table to store custom responses
class PollCustomResponse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    option_id: int = Field(foreign_key="polloption.id")
    user_id: int = Field(foreign_key="users.id")
    response_text: str = Field(max_length=200)
    created_at: datetime = Field(default=datetime.utcnow)
    
    option: "PollOption" = Relationship(back_populates="custom_responses")
    user: "User" = Relationship(back_populates="poll_custom_responses")

class PaginatedResponse(SQLModel):
    items: list
    total: int
    page: int
    size: int
    pages: int

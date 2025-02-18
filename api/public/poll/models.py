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

class PollStatus(str, Enum):
    DRAFT = "DRAFT"
    CLOSED = "CLOSED"
    PUBLISHED = "PUBLISHED"

class ReactionType(str, Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"

class PollBase(SQLModel):
    title: str = Field(max_length=100, index=True)
    description: Optional[str] = Field(max_length=500, nullable=True)
    type: PollType = Field(default=PollType.BINARY)
    is_anonymous: bool = Field(default=True)
    ends_at: Optional[datetime] = Field(nullable=True)
    scope: str = Field(max_length=100, nullable=True, description="The scope of the poll, e.g. 'GLOBAL', 'INTERNATINAL', 'NATIONAL', etc.")

class Poll(PollBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(max_length=100, index=True, unique=True)
    creator_id: int = Field(foreign_key="users.id")
    status: PollStatus = Field(default=PollStatus.DRAFT)
    created_at: datetime = Field(default=datetime.utcnow)
    updated_at: datetime = Field(default=datetime.utcnow)

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
from enum import Enum
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional
from pydantic import EmailStr
from api.utils.generic_models import UserCommunityLink, UserFollowLink

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    GUEST = "GUEST"
    MODERATOR = "MODERATOR"
    BOT = "BOT"

class UserBase(SQLModel):
    username: str = Field(max_length=50, unique=True, index=True)
    email: EmailStr = Field(unique=True, index=True)
    name: Optional[str] = Field(max_length=50, nullable=True)
    email_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    role: UserRole = Field(default=UserRole.USER)
    bio: Optional[str] = Field(default=None, max_length=500, nullable=True)
    location: Optional[str] = Field(default=None, max_length=100, nullable=True)
    website: Optional[str] = Field(default=None, max_length=100, nullable=True, regex=r"^https?://(?:www\.)?[a-zA-Z0-9]+\.[a-zA-Z0-9]+$")
    avatar: Optional[str] = Field(default=None, max_length=100, nullable=True)
    cover: Optional[str] = Field(default=None, max_length=100, nullable=True)
    gender: Optional[str] = Field(default=None, max_length=1, nullable=True)
    last_login: Optional[datetime] = Field(default=None)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now(timezone.utc), index=True, nullable=False)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    communities: list["Community"] = Relationship(back_populates="members", link_model=UserCommunityLink)
    followers: list["User"] = Relationship(
        back_populates="following",
        link_model=UserFollowLink,
        sa_relationship_kwargs={
            "primaryjoin": "User.id == UserFollowLink.followed_id",
            "secondaryjoin": "User.id == UserFollowLink.follower_id",
        }
    )
    following: list["User"] = Relationship(
        back_populates="followers",
        link_model=UserFollowLink,
        sa_relationship_kwargs={
            "primaryjoin": "User.id == UserFollowLink.follower_id",
            "secondaryjoin": "User.id == UserFollowLink.followed_id",
        }
    )
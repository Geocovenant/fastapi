from enum import Enum
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from typing import Optional, List
from pydantic import EmailStr
from api.utils.generic_models import UserCommunityLink, UserFollowLink

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    GUEST = "GUEST"
    MODERATOR = "MODERATOR"
    BOT = "BOT"

class UserBase(SQLModel):
    # Campos requeridos por Auth.js
    email: EmailStr = Field(..., unique=True, index=True)
    emailVerified: Optional[datetime] = Field(default=None)
    image: Optional[str] = Field(default=None, alias="avatar")
    
    # Campos personalizados existentes
    username: Optional[str] = Field(max_length=50, unique=True, index=True)
    name: Optional[str] = Field(max_length=50, nullable=True)
    is_active: Optional[bool] = Field(default=True)
    role: Optional[UserRole] = Field(default=UserRole.USER)
    bio: Optional[str] = Field(default=None, max_length=500, nullable=True)
    location: Optional[str] = Field(default=None, max_length=100, nullable=True)
    website: Optional[str] = Field(
        default=None, 
        max_length=100, 
        nullable=True, 
        regex=r"^https?://(?:www\.)?[a-zA-Z0-9]+\.[a-zA-Z0-9]+$"
    )
    cover: Optional[str] = Field(default=None, max_length=100, nullable=True)
    gender: Optional[str] = Field(default=None, max_length=1, nullable=True)
    last_login: Optional[datetime] = Field(default=None)

class User(UserBase, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relaciones para Auth.js
    accounts: List["Account"] = Relationship(back_populates="user")
    sessions: List["Session"] = Relationship(back_populates="user")
    
    # Tus relaciones existentes
    communities: List["Community"] = Relationship(back_populates="members", link_model=UserCommunityLink)
    followers: List["User"] = Relationship(
        back_populates="following",
        link_model=UserFollowLink,
        sa_relationship_kwargs={
            "primaryjoin": "User.id == UserFollowLink.followed_id",
            "secondaryjoin": "User.id == UserFollowLink.follower_id",
        }
    )
    following: List["User"] = Relationship(
        back_populates="followers",
        link_model=UserFollowLink,
        sa_relationship_kwargs={
            "primaryjoin": "User.id == UserFollowLink.follower_id",
            "secondaryjoin": "User.id == UserFollowLink.followed_id",
        }
    )
    polls: List["Poll"] = Relationship(back_populates="creator")

# Modelos adicionales requeridos por Auth.js
class Account(SQLModel, table=True):
    __tablename__ = "accounts"
    id: Optional[int] = Field(default=None, primary_key=True)
    userId: int = Field(foreign_key="users.id")
    type: str = Field(...)
    provider: str = Field(...)
    providerAccountId: str = Field(...)
    refresh_token: Optional[str] = Field(default=None)
    access_token: Optional[str] = Field(default=None)
    expires_at: Optional[int] = Field(default=None)
    token_type: Optional[str] = Field(default=None)
    scope: Optional[str] = Field(default=None)
    id_token: Optional[str] = Field(default=None)
    session_state: Optional[str] = Field(default=None)
    
    user: User = Relationship(back_populates="accounts")

class Session(SQLModel, table=True):
    __tablename__ = "sessions"
    id: Optional[int] = Field(default=None, primary_key=True)
    userId: int = Field(foreign_key="users.id")
    expires: datetime = Field(...)
    sessionToken: str = Field(...)
    
    user: User = Relationship(back_populates="sessions")

class VerificationToken(SQLModel, table=True):
    __tablename__ = "verification_token"
    identified: str = Field(..., primary_key=True)
    token: str = Field(..., primary_key=True)
    expires: datetime = Field(...)
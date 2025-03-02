from enum import Enum
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from pydantic import EmailStr, field_validator
from api.utils.generic_models import UserCommunityLink, UserFollowLink
import re

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    GUEST = "GUEST"
    MODERATOR = "MODERATOR"
    BOT = "BOT"

class UserBase(SQLModel):
    # Fields required by Auth.js
    email: EmailStr = Field(..., unique=True, index=True)
    emailVerified: Optional[datetime] = Field(default=None)
    image: Optional[str] = Field(default=None, alias="avatar")
    
    # Existing custom fields
    username: Optional[str] = Field(max_length=50, unique=True, index=True)
    name: Optional[str] = Field(max_length=50, nullable=True)
    is_active: Optional[bool] = Field(default=True)
    role: Optional[UserRole] = Field(default=UserRole.USER)
    bio: Optional[str] = Field(default=None, max_length=500, nullable=True)
    country: Optional[str] = Field(default=None, max_length=100, nullable=True)
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
    
    # Relationships for Auth.js
    accounts: list["Account"] = Relationship(back_populates="user")
    sessions: list["Session"] = Relationship(back_populates="user")
    
    # Your existing relationships
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
    polls: list["Poll"] = Relationship(back_populates="creator")
    poll_votes: list["PollVote"] = Relationship(back_populates="user")
    poll_reactions: list["PollReaction"] = Relationship(back_populates="user")
    poll_comments: list["PollComment"] = Relationship(back_populates="user")
    
    # New relationships for debates
    debates_created: list["Debate"] = Relationship(
        back_populates="creator",
        sa_relationship_kwargs={"foreign_keys": "[Debate.creator_id]"}
    )
    debates_approved: list["Debate"] = Relationship(
        back_populates="approved_by",
        sa_relationship_kwargs={"foreign_keys": "[Debate.approved_by_id]"}
    )
    debates_rejected: list["Debate"] = Relationship(
        back_populates="rejected_by",
        sa_relationship_kwargs={"foreign_keys": "[Debate.rejected_by_id]"}
    )
    
    # Add poll_custom_responses here
    poll_custom_responses: list["PollCustomResponse"] = Relationship(back_populates="user")

    # Relationships for projects
    projects: list["Project"] = Relationship(back_populates="creator")
    project_commitments: list["ProjectCommitment"] = Relationship(back_populates="user")
    project_donations: list["ProjectDonation"] = Relationship(back_populates="user")

    # Relationships for issues
    issues_created: list["Issue"] = Relationship(back_populates="creator")
    issue_supports: list["IssueSupport"] = Relationship(back_populates="user")
    issue_comments: list["IssueComment"] = Relationship(back_populates="user")
    issue_updates: list["IssueUpdate"] = Relationship(back_populates="user")

# Additional models required by Auth.js
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

class UserUpdateSchema(SQLModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    cover: Optional[str] = None
    image: Optional[str] = None
    gender: Optional[str] = None

class UsernameUpdateSchema(SQLModel):
    username: str
    
    @field_validator('username')
    def validate_username(cls, v):
        # List of reserved words that cannot be used as username
        reserved_words = ["anonymous", "admin", "system", "moderator", "support"]
        
        # Inappropriate words that should not be allowed
        inappropriate_words = ["profanity1", "profanity2", "badword"]  # Replace with actual words
        
        # Username must start with a letter
        # Can only contain letters, numbers, and underscores
        # Length between 3 and 30 characters
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{2,29}$', v):
            raise ValueError(
                "Username must start with a letter and can only contain letters, numbers, and underscores. Length must be between 3 and 30 characters."
            )
        
        # Check if the username is in the list of reserved words
        if v.lower() in reserved_words:
            raise ValueError(
                f"'{v}' is a reserved username and cannot be used"
            )
        
        # Check if the username contains inappropriate words
        for word in inappropriate_words:
            if word.lower() in v.lower():
                raise ValueError(
                    "Username contains inappropriate content"
                )
                
        return v

# Update the schema for automatic username generation
class GenerateUsernameSchema(SQLModel):
    base_name: str
    # The base_name field now represents the username proposed by the user
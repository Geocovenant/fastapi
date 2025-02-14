from sqlmodel import SQLModel, Field
from typing import Optional

class UserCommunityLink(SQLModel, table=True):
    user_id: Optional[int] = Field(foreign_key="user.id", primary_key=True)
    community_id: Optional[int] = Field(foreign_key="community.id", primary_key=True)

class UserFollowLink(SQLModel, table=True):
    follower_id: int = Field(foreign_key="user.id", primary_key=True)
    followed_id: int = Field(foreign_key="user.id", primary_key=True)
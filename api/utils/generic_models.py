from sqlmodel import SQLModel, Field
from typing import Optional

class UserCommunityLink(SQLModel, table=True):
    user_id: Optional[int] = Field(foreign_key="users.id", primary_key=True)
    community_id: Optional[int] = Field(foreign_key="community.id", primary_key=True)

class UserFollowLink(SQLModel, table=True):
    follower_id: int = Field(foreign_key="users.id", primary_key=True)
    followed_id: int = Field(foreign_key="users.id", primary_key=True)

class PollCommunityLink(SQLModel, table=True):
    poll_id: int = Field(foreign_key="poll.id", primary_key=True)
    community_id: int = Field(foreign_key="community.id", primary_key=True)

class PollTagLink(SQLModel, table=True):
    poll_id: int = Field(foreign_key="poll.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)
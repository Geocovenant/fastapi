from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from api.utils.generic_models import PollTagLink, DebateTagLink, IssueTagLink

class TagBase(SQLModel):
    name: str = Field(max_length=50, unique=True, index=True)

class Tag(TagBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Relationships
    polls: list["Poll"] = Relationship(back_populates="tags", link_model=PollTagLink)
    debates: list["Debate"] = Relationship(back_populates="tags", link_model=DebateTagLink)
    issues: list["Issue"] = Relationship(back_populates="tags", link_model=IssueTagLink)

class TagCreate(TagBase):
    pass

class TagRead(TagBase):
    id: int

class TagUpdate(TagBase):
    pass

class TagDelete(TagBase):
    pass
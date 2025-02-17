from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from api.utils.generic_models import PollTagLink

class TagBase(SQLModel):
    name: str = Field(max_length=50, unique=True, index=True)

class Tag(TagBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Relationships
    polls: list["Poll"] = Relationship(back_populates="tags", link_model=PollTagLink)

class TagCreate(TagBase):
    pass

class TagRead(TagBase):
    id: int

class TagUpdate(TagBase):
    pass

class TagDelete(TagBase):
    pass
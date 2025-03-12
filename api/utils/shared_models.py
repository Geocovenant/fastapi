from sqlmodel import SQLModel
from typing import Optional

class UserMinimal(SQLModel):
    id: int
    username: str
    image: Optional[str] = None

class CommunityMinimal(SQLModel):
    id: int
    name: str
    cca2: Optional[str] = None 
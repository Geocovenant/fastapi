from sqlmodel import SQLModel
from typing import Optional

class UserMinimal(SQLModel):
    id: int
    username: str
    image: Optional[str] = None 
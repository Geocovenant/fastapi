from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional

class Session(SQLModel, table=True):
    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default=datetime.utcnow)
    expires_at: datetime
    
    # Relationship
    user: "User" = Relationship(back_populates="sessions") 
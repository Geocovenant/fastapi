from sqlmodel import Field, SQLModel, Relationship
from typing import Optional

class SupportedLanguage(SQLModel, table=True):
    code: str = Field(primary_key=True, max_length=5)  # e.g., "es", "en-US"
    name: str = Field(max_length=50)
    native_name: str = Field(max_length=50)
    is_active: bool = Field(default=True)

class CommunityTranslation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    community_id: int = Field(foreign_key="community.id", index=True)
    language_code: str = Field(max_length=5, foreign_key="supportedlanguage.code", index=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(max_length=500)
    
    # Relationships
    community: "Community" = Relationship(back_populates="translations")
    language: SupportedLanguage = Relationship()
    
    class Config:
        # Garantiza que no hay duplicados para la misma comunidad e idioma
        unique_together = [("community_id", "language_code")] 
from datetime import datetime
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship, Column, DateTime
from typing import Optional, List
from pydantic import EmailStr, field_validator
import sqlalchemy

class ReportType(str, Enum):
    """Tipos de elementos que pueden ser reportados"""
    POLL = "POLL"
    DEBATE = "DEBATE"
    PROJECT = "PROJECT"
    ISSUE = "ISSUE"
    COMMENT = "COMMENT"
    USER = "USER"

class ReportStatus(str, Enum):
    """Estados posibles para un reporte"""
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"

class ReportReason(str, Enum):
    """Razones comunes para reportar contenido"""
    INAPPROPRIATE = "INAPPROPRIATE"
    SPAM = "SPAM"
    HARMFUL = "HARMFUL"
    MISINFORMATION = "MISINFORMATION"
    HATE_SPEECH = "HATE_SPEECH"
    SCAM = "SCAM"
    FALSE_INFO = "FALSE_INFO"
    DUPLICATED = "DUPLICATED"
    FAKE = "FAKE"
    OTHER = "OTHER"

class ReportBase(SQLModel):
    """Modelo base para reportes"""
    type: ReportType = Field(...)
    reason: ReportReason = Field(...)
    details: Optional[str] = Field(default=None, max_length=1000)
    item_id: int = Field(...)
    status: ReportStatus = Field(default=ReportStatus.PENDING)
    resolution_notes: Optional[str] = Field(default=None, max_length=1000)

class Report(ReportBase, table=True):
    """Modelo de tabla para reportes"""
    __tablename__ = "reports"
    
    # Campos principales
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True)))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    resolved_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    reporter_id: int = Field(foreign_key="users.id")
    resolved_by_id: Optional[int] = Field(default=None, foreign_key="users.id")
    
    # Relaciones
    reporter: "User" = Relationship(
        back_populates="reports_created",
        sa_relationship_kwargs={"foreign_keys": "[Report.reporter_id]"}
    )
    resolved_by: Optional["User"] = Relationship(
        back_populates="reports_resolved",
        sa_relationship_kwargs={"foreign_keys": "[Report.resolved_by_id]"}
    )
    
    # Índices para optimizar consultas comunes
    __table_args__ = (
        sqlalchemy.Index("idx_report_type_item", "type", "item_id"),
        sqlalchemy.Index("idx_report_status", "status"),
        sqlalchemy.Index("idx_report_reporter", "reporter_id"),
    )

class ReportCreate(SQLModel):
    """Esquema para crear un nuevo reporte"""
    item_type: ReportType
    item_id: int
    reason: ReportReason
    details: Optional[str] = None

class ReportResponse(SQLModel):
    """Esquema para respuestas de reporte"""
    id: int
    type: ReportType
    reason: ReportReason
    details: Optional[str]
    item_id: int
    status: ReportStatus
    created_at: datetime
    reporter_id: int

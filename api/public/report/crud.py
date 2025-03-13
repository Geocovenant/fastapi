from sqlmodel import select, Session, or_
from datetime import datetime
from typing import Optional

from .models import Report, ReportCreate, ReportStatus
from api.public.user.models import User

def create_report(db: Session, report_data: ReportCreate, reporter_id: int) -> Report:
    """Create a new report"""
    db_report = Report(
        type=report_data.item_type,
        reason=report_data.reason,
        details=report_data.details,
        item_id=report_data.item_id,
        reporter_id=reporter_id
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

def get_reports(db: Session, skip: int = 0, limit: int = 100) -> list[Report]:
    """Get all reports"""
    return db.exec(select(Report).offset(skip).limit(limit)).all()

def get_report(db: Session, report_id: int) -> Optional[Report]:
    """Get a specific report by ID"""
    return db.get(Report, report_id)

def get_reports_by_status(db: Session, status: ReportStatus, skip: int = 0, limit: int = 100) -> list[Report]:
    """Get reports by status"""
    return db.exec(select(Report).where(Report.status == status).offset(skip).limit(limit)).all()

def update_report_status(db: Session, report_id: int, status: ReportStatus, resolver_id: int, notes: str = None) -> Optional[Report]:
    """Update the status of a report"""
    db_report = db.get(Report, report_id)
    if not db_report:
        return None
    
    db_report.status = status
    db_report.updated_at = datetime.utcnow()
    
    if status in [ReportStatus.RESOLVED, ReportStatus.REJECTED]:
        db_report.resolved_at = datetime.utcnow()
        db_report.resolved_by_id = resolver_id
        
    if notes:
        db_report.resolution_notes = notes
        
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

def get_reports_by_item(db: Session, item_type: str, item_id: int) -> list[Report]:
    """Get all reports for a specific item"""
    return db.exec(
        select(Report)
        .where(Report.type == item_type, Report.item_id == item_id)
    ).all()

def check_existing_report(db: Session, item_type: str, item_id: int, reporter_id: int) -> bool:
    """Check if a user has already reported this item"""
    existing_report = db.exec(
        select(Report).where(
            Report.type == item_type,
            Report.item_id == item_id,
            Report.reporter_id == reporter_id,
            or_(
                Report.status == ReportStatus.PENDING,
                Report.status == ReportStatus.UNDER_REVIEW
            )
        )
    ).first()
    
    return existing_report is not None

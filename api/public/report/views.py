from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from api.auth.dependencies import get_current_user
from api.database import get_session
from .models import ReportCreate, ReportResponse, ReportStatus
from .crud import (
    create_report,
    get_reports,
    get_report,
    update_report_status,
    check_existing_report,
    get_reports_by_status
)
from api.public.user.models import User, UserRole

router = APIRouter()

@router.post("/", response_model=ReportResponse, status_code=201)
def create_new_report(
    report_data: ReportCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new report"""
    # Check if the user has already reported this item
    if check_existing_report(db, report_data.item_type, report_data.item_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reported this item before."
        )
    
    return create_report(db, report_data, current_user.id)

@router.get("/", response_model=list[ReportResponse])
def read_reports(
    skip: int = 0,
    limit: int = 100,
    status: ReportStatus = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get list of reports (only for administrators and moderators)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view reports."
        )
    
    if status:
        return get_reports_by_status(db, status, skip, limit)
    return get_reports(db, skip, limit)

@router.get("/{report_id}", response_model=ReportResponse)
def read_report(
    report_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific report (only for administrators and moderators)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view reports."
        )
    
    report = get_report(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found."
        )
    return report

@router.patch("/{report_id}/status", response_model=ReportResponse)
def update_status(
    report_id: int,
    status: ReportStatus,
    notes: str = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update the status of a report (only for administrators and moderators)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update reports."
        )
    
    updated_report = update_report_status(db, report_id, status, current_user.id, notes)
    if updated_report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found."
        )
    return updated_report

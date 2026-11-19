from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from apps.api.src.core.database import get_db, set_tenant_session
from apps.api.src.api.deps import get_current_user, get_current_tenant
from apps.api.src.models.user import User
from apps.api.src.models.tenant import Organization
from apps.api.src.models.creator import Creator
from apps.api.src.models.creator_alert import CreatorAlert
from apps.api.src.models.monitoring_log import CreatorMonitoringLog
from apps.api.src.services.monitoring.monitoring_engine import CreatorMonitoringEngine

router = APIRouter(prefix="/monitoring", tags=["Creator Page Monitoring Engine"])

class ConfigureScheduleRequest(BaseModel):
    interval: str = Field("daily", description="Monitoring interval: 'one-time', 'daily', 'weekly', 'custom'")
    status: str = Field("active", description="Monitoring status: 'active', 'paused', 'unmonitored'")
    custom_interval_hours: int = Field(24, ge=1, le=720, description="Interval in hours if interval is 'custom'")
    alert_preferences: Optional[Dict[str, bool]] = Field(None, description="Notification preference toggles")

class CheckNowRequest(BaseModel):
    incoming_feed: Optional[List[Dict[str, Any]]] = Field(None, description="Simulated or ingested feed items")
    simulate_error: Optional[str] = Field(None, description="Simulate an error or unreachable source")

@router.get("/creators/{creator_id}/dashboard")
def get_creator_monitoring_dashboard(
    creator_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """
    Returns full monitoring dashboard metrics for a creator:
    Profile, schedule, last check, next check, content themes, emerging problems, and recent alerts.
    """
    set_tenant_session(db, tenant.id)
    try:
        dashboard = CreatorMonitoringEngine.get_creator_dashboard(db, creator_id, tenant.id)
        return dashboard
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/creators/{creator_id}/configure")
def configure_creator_schedule(
    creator_id: str,
    data: ConfigureScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """
    Configures monitoring schedule, interval (daily/weekly/custom), and alert notification preferences.
    """
    set_tenant_session(db, tenant.id)
    try:
        updated_creator = CreatorMonitoringEngine.configure_schedule(
            db=db,
            creator_id=creator_id,
            tenant_id=tenant.id,
            interval=data.interval,
            status=data.status,
            custom_interval_hours=data.custom_interval_hours,
            alert_preferences=data.alert_preferences
        )
        return {
            "creator_id": updated_creator.id,
            "username": updated_creator.username,
            "monitoring_status": updated_creator.monitoring_status,
            "monitoring_interval": updated_creator.monitoring_interval,
            "custom_interval_hours": updated_creator.custom_interval_hours,
            "next_check_due": updated_creator.next_check_due.isoformat() if updated_creator.next_check_due else None,
            "alert_preferences": updated_creator.alert_preferences
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/creators/{creator_id}/check-now")
def run_immediate_check(
    creator_id: str,
    data: CheckNowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """
    Executes an on-demand monitoring check:
    Computes SHA-256 deduplication hashes, detects semantic theme shifts,
    aggregates audience complaints, and dispatches automated alerts.
    """
    set_tenant_session(db, tenant.id)
    try:
        result = CreatorMonitoringEngine.execute_monitoring_check(
            db=db,
            creator_id=creator_id,
            tenant_id=tenant.id,
            incoming_feed=data.incoming_feed,
            simulate_error=data.simulate_error
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/creators/{creator_id}/logs")
def get_monitoring_logs(
    creator_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Lists historical monitoring logs for a creator."""
    set_tenant_session(db, tenant.id)
    logs = db.query(CreatorMonitoringLog).filter(
        CreatorMonitoringLog.creator_id == creator_id,
        CreatorMonitoringLog.tenant_id == tenant.id
    ).order_by(desc(CreatorMonitoringLog.checked_at)).limit(50).all()

    return {
        "creator_id": creator_id,
        "count": len(logs),
        "logs": [
            {
                "id": l.id,
                "checked_at": l.checked_at.isoformat(),
                "status": l.status,
                "posts_checked": l.posts_checked,
                "new_posts_count": l.new_posts_count,
                "changes_detected": l.changes_detected,
                "summary": l.summary,
                "error_message": l.error_message
            }
            for l in logs
        ]
    }

@router.get("/alerts")
def list_alerts(
    unread_only: bool = False,
    creator_id: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Lists monitoring alerts across all tracked creators within the current tenant."""
    set_tenant_session(db, tenant.id)
    query = db.query(CreatorAlert).filter(CreatorAlert.tenant_id == tenant.id)

    if unread_only:
        query = query.filter(CreatorAlert.is_read == False)
    if creator_id:
        query = query.filter(CreatorAlert.creator_id == creator_id)
    if severity:
        query = query.filter(CreatorAlert.severity == severity)

    alerts = query.order_by(desc(CreatorAlert.created_at)).all()
    return {
        "count": len(alerts),
        "unread_count": sum(1 for a in alerts if not a.is_read),
        "alerts": [
            {
                "id": a.id,
                "creator_id": a.creator_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "data": a.data,
                "is_read": a.is_read,
                "read_at": a.read_at.isoformat() if a.read_at else None,
                "created_at": a.created_at.isoformat()
            }
            for a in alerts
        ]
    }

@router.post("/alerts/{alert_id}/read")
def mark_alert_as_read(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Marks a single alert as read."""
    set_tenant_session(db, tenant.id)
    alert = db.query(CreatorAlert).filter(
        CreatorAlert.id == alert_id,
        CreatorAlert.tenant_id == tenant.id
    ).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found in tenant workspace.")

    alert.is_read = True
    alert.read_at = datetime.now(timezone.utc)
    db.commit()

    return {"id": alert.id, "is_read": True, "read_at": alert.read_at.isoformat()}

@router.post("/alerts/read-all")
def mark_all_alerts_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Marks all unread alerts in the tenant workspace as read."""
    set_tenant_session(db, tenant.id)
    now = datetime.now(timezone.utc)
    unread_alerts = db.query(CreatorAlert).filter(
        CreatorAlert.tenant_id == tenant.id,
        CreatorAlert.is_read == False
    ).all()

    for a in unread_alerts:
        a.is_read = True
        a.read_at = now

    db.commit()
    return {"status": "success", "marked_read_count": len(unread_alerts)}

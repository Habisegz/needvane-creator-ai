from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from apps.api.src.core.database import get_db, set_tenant_session
from apps.api.src.services.creators.discovery_service import CreatorDiscoveryService
from apps.api.src.services.monitoring.monitoring_engine import CreatorMonitoringEngine
from apps.api.src.api.deps import get_current_user, get_current_tenant
from apps.api.src.models.user import User
from apps.api.src.models.tenant import Organization
from apps.api.src.models.creator import Creator
from apps.api.src.models.partnership import PartnershipAgreement

router = APIRouter(prefix="/creators", tags=["Creator Discovery & Monitoring"])

class CreatorCreateRequest(BaseModel):
    username: str = Field(..., min_length=2)
    display_name: Optional[str] = None
    platform: str = Field("instagram")
    profile_url: str
    follower_count: int = Field(0, ge=0)
    engagement_rate: float = Field(0.0, ge=0.0)
    niche_categories: List[str] = Field(default_factory=list)
    public_business_email: Optional[str] = None
    data_tier: str = Field("Tier C")

class CreatorSearchRequest(BaseModel):
    niche: Optional[str] = None
    platform: Optional[str] = None
    min_followers: int = Field(50000, description="Minimum follower count (default: 50,000)")
    max_followers: int = Field(150000, description="Maximum follower count (default: 150,000)")
    country_code: Optional[str] = None

class KindredSearchRequest(BaseModel):
    target_topic: str = Field(..., min_length=3, description="Topic, pain point, or niche concept")
    limit: int = Field(3, ge=1, le=10, description="Number of kindred creators to discover")

class BindProductRequest(BaseModel):
    product_id: str
    product_title: str
    product_slug: str
    creator_usernames: List[str]
    creator_split_percent: float = Field(30.0, ge=1.0, le=99.0)
    platform_split_percent: float = Field(70.0, ge=1.0, le=99.0)

class CreatorImportRequest(BaseModel):
    records: List[dict]
    data_tier: str = Field("Tier C", description="Data Tier (Tier A, Tier B, Tier C, Tier D)")

class ConfigureScheduleRequest(BaseModel):
    interval: str = Field("daily", description="Monitoring interval: 'one-time', 'daily', 'weekly', 'custom'")
    status: str = Field("active", description="Monitoring status: 'active', 'paused', 'unmonitored'")
    custom_interval_hours: int = Field(24, ge=1, le=720)
    alert_preferences: Optional[Dict[str, bool]] = None

class CheckNowRequest(BaseModel):
    incoming_feed: Optional[List[Dict[str, Any]]] = None
    simulate_error: Optional[str] = None

@router.get("/feasibility-report")
def get_data_access_feasibility_report():
    """Returns the platform-by-platform Data Access Feasibility Report and Tier guidelines."""
    return {
        "status": "active",
        "data_tiers": {
            "Tier A": "Official API with Creator OAuth authorization",
            "Tier B": "Licensed third-party creator discovery data providers",
            "Tier C": "User-supplied imports (CSV, analytics exports, comment lists)",
            "Tier D": "Manual verified research entered by the user"
        },
        "platforms_assessed": ["Instagram", "YouTube", "TikTok", "X / Twitter", "Facebook"],
        "default_follower_range": "50,000 to 150,000 (configurable)",
        "scraping_policy": "Zero unauthorized scraping; compliance with NDPA 2023, GDPR, and Platform Terms"
    }

@router.post("/search")
def search_creators(
    data: CreatorSearchRequest,
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Filters verified creators by niche, platform, follower range (50k to 150k), and country."""
    results = CreatorDiscoveryService.search_creators(
        niche=data.niche,
        platform=data.platform,
        min_followers=data.min_followers,
        max_followers=data.max_followers,
        country_code=data.country_code
    )
    return {
        "count": len(results),
        "min_followers": data.min_followers,
        "max_followers": data.max_followers,
        "creators": results
    }

@router.post("/kindred")
def discover_kindred_creators(
    data: KindredSearchRequest,
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """
    Kindred Lookalike Search (SPEC.md Section 3B):
    Discovers 2, 3, or more creators producing content on similar concepts using vector similarity.
    """
    kindred = CreatorDiscoveryService.find_kindred_lookalike_creators(
        target_topic=data.target_topic,
        limit=data.limit
    )
    return {
        "target_topic": data.target_topic,
        "matched_count": len(kindred),
        "kindred_creators": kindred
    }

@router.post("/bind-product")
def bind_product_to_creators(
    data: BindProductRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """
    Ties one digital product to 2, 3, or more kindred creators simultaneously.
    Generates unique referral codes, tracking URLs, revenue splits, and tailored pitch emails.
    """
    set_tenant_session(db, tenant.id)
    creators_to_bind = [
        c for c in CreatorDiscoveryService.MOCK_CREATOR_REGISTRY
        if c["username"] in data.creator_usernames
    ]

    # Also check DB creators if any match
    db_creators = db.query(Creator).filter(
        Creator.tenant_id == tenant.id,
        Creator.username.in_(data.creator_usernames)
    ).all()
    for dbc in db_creators:
        if not any(c["username"] == dbc.username for c in creators_to_bind):
            creators_to_bind.append({
                "username": dbc.username,
                "display_name": dbc.display_name or dbc.username,
                "platform": dbc.platform,
                "follower_count": dbc.follower_count,
                "engagement_rate": float(dbc.engagement_rate or 0.0),
                "niche_categories": dbc.niche_categories or [],
                "public_business_email": dbc.public_business_email,
                "data_tier": dbc.data_tier
            })

    if not creators_to_bind:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching creators found for provided usernames"
        )

    agreements = CreatorDiscoveryService.bind_product_to_multiple_creators(
        product_id=data.product_id,
        product_title=data.product_title,
        product_slug=data.product_slug,
        creators=creators_to_bind,
        creator_split_percent=data.creator_split_percent,
        platform_split_percent=data.platform_split_percent
    )

    return {
        "product_id": data.product_id,
        "product_title": data.product_title,
        "bound_creators_count": len(agreements),
        "partnerships": agreements
    }

@router.post("", status_code=status.HTTP_201_CREATED)
def create_creator(
    data: CreatorCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Creates a creator in the tenant's workspace."""
    set_tenant_session(db, tenant.id)
    creator = Creator(
        tenant_id=tenant.id,
        username=data.username,
        display_name=data.display_name or data.username,
        platform=data.platform,
        profile_url=data.profile_url,
        follower_count=data.follower_count,
        engagement_rate=data.engagement_rate,
        niche_categories=data.niche_categories,
        public_business_email=data.public_business_email,
        data_tier=data.data_tier,
        monitoring_status="active",
        monitoring_interval="daily"
    )
    db.add(creator)
    db.commit()
    db.refresh(creator)
    return {
        "id": creator.id,
        "username": creator.username,
        "display_name": creator.display_name,
        "platform": creator.platform,
        "follower_count": creator.follower_count,
        "monitoring_status": creator.monitoring_status,
        "created_at": creator.created_at.isoformat()
    }

@router.get("")
def list_creators(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Lists all creators registered within the tenant workspace."""
    set_tenant_session(db, tenant.id)
    creators = db.query(Creator).filter(Creator.tenant_id == tenant.id).order_by(desc(Creator.created_at)).all()
    return {
        "count": len(creators),
        "creators": [
            {
                "id": c.id,
                "username": c.username,
                "display_name": c.display_name,
                "platform": c.platform,
                "follower_count": c.follower_count,
                "engagement_rate": float(c.engagement_rate or 0.0),
                "data_tier": c.data_tier,
                "monitoring_status": c.monitoring_status,
                "last_checked_at": c.last_checked_at.isoformat() if c.last_checked_at else None
            }
            for c in creators
        ]
    }

@router.get("/{creator_id}")
def get_creator(
    creator_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Gets a specific creator by ID."""
    set_tenant_session(db, tenant.id)
    creator = db.query(Creator).filter(
        Creator.id == creator_id,
        Creator.tenant_id == tenant.id
    ).first()
    if not creator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")

    return {
        "id": creator.id,
        "username": creator.username,
        "display_name": creator.display_name,
        "platform": creator.platform,
        "profile_url": creator.profile_url,
        "follower_count": creator.follower_count,
        "engagement_rate": float(creator.engagement_rate or 0.0),
        "niche_categories": creator.niche_categories or [],
        "data_tier": creator.data_tier,
        "monitoring_status": creator.monitoring_status,
        "monitoring_interval": creator.monitoring_interval,
        "last_checked_at": creator.last_checked_at.isoformat() if creator.last_checked_at else None,
        "next_check_due": creator.next_check_due.isoformat() if creator.next_check_due else None
    }

@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_creators(
    data: CreatorImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Authorised import of creator records (Tier C / Tier D) with automated tier tagging and DB persistence."""
    set_tenant_session(db, tenant.id)
    saved_creators = []
    for rec in data.records:
        username = rec.get("username", "creator")
        existing = db.query(Creator).filter(
            Creator.tenant_id == tenant.id,
            Creator.username == username
        ).first()

        if existing:
            existing.follower_count = rec.get("follower_count", existing.follower_count)
            existing.engagement_rate = rec.get("engagement_rate", existing.engagement_rate)
            existing.data_tier = data.data_tier
            saved_creators.append(existing)
        else:
            new_creator = Creator(
                tenant_id=tenant.id,
                username=username,
                display_name=rec.get("display_name", username),
                platform=rec.get("platform", "instagram"),
                profile_url=rec.get("profile_url", f"https://instagram.com/{username}"),
                follower_count=rec.get("follower_count", 50000),
                engagement_rate=rec.get("engagement_rate", 3.5),
                niche_categories=rec.get("niche_categories", ["general"]),
                public_business_email=rec.get("public_business_email"),
                data_tier=data.data_tier,
                monitoring_status="active",
                monitoring_interval="daily"
            )
            db.add(new_creator)
            saved_creators.append(new_creator)

    db.commit()
    for c in saved_creators:
        db.refresh(c)

    return {
        "imported_count": len(saved_creators),
        "data_tier": data.data_tier,
        "status": "success",
        "creator_ids": [c.id for c in saved_creators]
    }

# Creator Monitoring Resource Endpoints
@router.get("/{creator_id}/monitoring")
def get_creator_monitoring(
    creator_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Returns the monitoring dashboard for the specified creator."""
    set_tenant_session(db, tenant.id)
    try:
        return CreatorMonitoringEngine.get_creator_dashboard(db, creator_id, tenant.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{creator_id}/monitoring/configure")
def configure_creator_monitoring(
    creator_id: str,
    data: ConfigureScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Configures monitoring schedule for the specified creator."""
    set_tenant_session(db, tenant.id)
    try:
        updated = CreatorMonitoringEngine.configure_schedule(
            db=db,
            creator_id=creator_id,
            tenant_id=tenant.id,
            interval=data.interval,
            status=data.status,
            custom_interval_hours=data.custom_interval_hours,
            alert_preferences=data.alert_preferences
        )
        return {
            "creator_id": updated.id,
            "username": updated.username,
            "monitoring_status": updated.monitoring_status,
            "monitoring_interval": updated.monitoring_interval,
            "next_check_due": updated.next_check_due.isoformat() if updated.next_check_due else None
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{creator_id}/monitoring/check-now")
def run_creator_monitoring_check(
    creator_id: str,
    data: CheckNowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Executes an immediate monitoring run on the specified creator."""
    set_tenant_session(db, tenant.id)
    try:
        return CreatorMonitoringEngine.execute_monitoring_check(
            db=db,
            creator_id=creator_id,
            tenant_id=tenant.id,
            incoming_feed=data.incoming_feed,
            simulate_error=data.simulate_error
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from apps.api.src.core.database import get_db, set_tenant_session
from apps.api.src.api.deps import get_current_user, get_current_tenant
from apps.api.src.models.user import User
from apps.api.src.models.tenant import Organization
from apps.api.src.models.creator import Creator
from apps.api.src.models.product import Product
from apps.api.src.models.unmet_demand import UnmetDemand
from apps.api.src.models.email_campaign import EmailCampaign, EmailDispatch
from apps.api.src.services.email.email_studio_service import EmailStudioService

router = APIRouter(prefix="/emails", tags=["Email Studio & Campaigns"])


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    template_type: str = Field(..., description="outreach, follow_up, affiliate_pitch, confirmation")
    subject_template: str = Field(..., min_length=3, max_length=500)
    body_html: str = Field(..., min_length=10)
    body_text: str = Field(..., min_length=10)
    tags: Optional[List[str]] = None


class PitchGenerateRequest(BaseModel):
    creator_id: str
    product_id: Optional[str] = None
    unmet_demand_id: Optional[str] = None
    split_ratio: Optional[str] = "70/30"
    sender_name: Optional[str] = "NeedVane Creator Partnerships"


class CreateCampaignRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    sender_email: str = Field(..., description="Sender email with verified domain")
    sender_name: str = Field("NeedVane Creator Partnerships", max_length=255)
    creator_ids: List[str] = Field(..., min_length=1)
    product_id: Optional[str] = None
    split_ratio: Optional[str] = "70/30"


class ReplyWebhookRequest(BaseModel):
    creator_id: str
    reply_body: Optional[str] = "Yes, I'm interested in reviewing the chapters."


class BounceWebhookRequest(BaseModel):
    creator_id: str
    event_type: Optional[str] = "bounce"  # bounce or unsubscribe


@router.get("/templates")
def list_templates(
    template_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    return EmailStudioService.list_templates(db, tenant_id=tenant.id, template_type=template_type)


@router.post("/templates", status_code=status.HTTP_201_CREATED)
def create_template(
    payload: CreateTemplateRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    return EmailStudioService.create_custom_template(
        db=db,
        tenant_id=tenant.id,
        name=payload.name,
        template_type=payload.template_type,
        subject_template=payload.subject_template,
        body_html=payload.body_html,
        body_text=payload.body_text,
        tags=payload.tags
    )


@router.post("/pitch/generate")
def generate_pitch(
    payload: PitchGenerateRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    creator = db.query(Creator).filter(Creator.id == payload.creator_id, Creator.tenant_id == tenant.id).first()
    if not creator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")

    product = db.query(Product).filter(Product.id == payload.product_id).first() if payload.product_id else None
    unmet = db.query(UnmetDemand).filter(UnmetDemand.id == payload.unmet_demand_id).first() if payload.unmet_demand_id else None

    pitch = EmailStudioService.generate_personalized_pitch(
        creator=creator,
        product=product,
        unmet_demand=unmet,
        split_ratio=payload.split_ratio,
        sender_name=payload.sender_name
    )
    return pitch


@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CreateCampaignRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    campaign = EmailStudioService.create_campaign_with_sequences(
        db=db,
        tenant_id=tenant.id,
        name=payload.name,
        sender_email=payload.sender_email,
        sender_name=payload.sender_name,
        creator_ids=payload.creator_ids,
        product_id=payload.product_id,
        split_ratio=payload.split_ratio
    )
    return {
        "id": campaign.id,
        "tenant_id": campaign.tenant_id,
        "name": campaign.name,
        "product_id": campaign.product_id,
        "status": campaign.status,
        "sender_name": campaign.sender_name,
        "sender_email": campaign.sender_email,
        "target_split_percentage": campaign.target_split_percentage,
        "sequences": [
            {
                "id": s.id,
                "step_number": s.step_number,
                "delay_days": s.delay_days,
                "subject_template": s.subject_template,
                "body_template": s.body_template
            }
            for s in campaign.sequences
        ]
    }


@router.get("/campaigns")
def list_campaigns(
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    return db.query(EmailCampaign).filter(EmailCampaign.tenant_id == tenant.id).all()


@router.get("/campaigns/{campaign_id}/dispatches")
def list_dispatches(
    campaign_id: str,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    return db.query(EmailDispatch).filter(
        EmailDispatch.campaign_id == campaign_id,
        EmailDispatch.tenant_id == tenant.id
    ).order_by(EmailDispatch.scheduled_at.asc()).all()


@router.post("/webhooks/reply")
def handle_reply(
    payload: ReplyWebhookRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    return EmailStudioService.handle_incoming_reply(db, tenant_id=tenant.id, creator_id=payload.creator_id)


@router.post("/webhooks/bounce")
def handle_bounce(
    payload: BounceWebhookRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    return EmailStudioService.handle_bounce_or_unsubscribe(
        db, tenant_id=tenant.id, creator_id=payload.creator_id, event_type=payload.event_type
    )


@router.post("/dispatch/run")
def trigger_dispatch_run(
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    sent = EmailStudioService.dispatch_pending_emails(db, tenant_id=tenant.id)
    return {"dispatched_count": len(sent), "dispatches": [{"id": str(d.id), "recipient": d.recipient_email, "status": d.status} for d in sent]}

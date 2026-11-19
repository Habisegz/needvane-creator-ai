from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.src.core.database import get_db, set_tenant_session
from apps.api.src.api.deps import get_current_user, get_current_tenant
from apps.api.src.models.user import User
from apps.api.src.models.tenant import Organization
from apps.api.src.models.partnership_deal import (
    PartnershipDeal,
    DealStageHistory,
    CreatorReferralLink,
    DealStage
)
from apps.api.src.services.partnership.deal_service import PartnershipService, VALID_STAGES

router = APIRouter(prefix="/partnerships", tags=["Partnership CRM"])

STAGE_METADATA = [
    {"stage": "discovered", "order": 1, "label": "Discovered", "description": "Creator discovered via lookalike engine or intelligence radar"},
    {"stage": "researched", "order": 2, "label": "Researched", "description": "Audience signals and content analysis completed"},
    {"stage": "contact_identified", "order": 3, "label": "Contact Identified", "description": "Creator business contact email and DM channel validated"},
    {"stage": "email_drafted", "order": 4, "label": "Email Drafted", "description": "Personalized co-creation outreach email generated"},
    {"stage": "awaiting_approval", "order": 5, "label": "Awaiting Approval", "description": "Outreach pitch awaiting campaign manager review"},
    {"stage": "proposal_sent", "order": 6, "label": "Proposal Sent", "description": "Outreach pitch sent via Email Studio dispatcher"},
    {"stage": "follow_up_required", "order": 7, "label": "Follow-Up Required", "description": "Initial sequence dispatched, follow-up scheduled"},
    {"stage": "interested", "order": 8, "label": "Interested", "description": "Creator replied with positive intent or feedback"},
    {"stage": "negotiation", "order": 9, "label": "Negotiation", "description": "Aligning on revenue split, bonus packages, and launch schedule"},
    {"stage": "partnership_approved", "order": 10, "label": "Partnership Approved", "description": "Agreement approved, co-creation contract terms generated"},
    {"stage": "product_launched", "order": 11, "label": "Product Launched", "description": "Digital publication live on sales landing page with ?ref tracking"},
    {"stage": "active_partnership", "order": 12, "label": "Active Partnership", "description": "Ongoing campaign generating sales and automated split disbursements"},
    {"stage": "closed_inactive", "order": 13, "label": "Closed/Inactive", "description": "Deal concluded, paused, or disqualified"}
]

class CreateDealRequest(BaseModel):
    creator_id: str
    title: str
    product_id: Optional[str] = None
    stage: str = Field(default="discovered")
    creator_split_percentage: int = Field(default=70, ge=1, le=99)
    deal_value_estimate: int = Field(default=50000)
    custom_notes: Optional[str] = None

class TransitionStageRequest(BaseModel):
    to_stage: str
    notes: Optional[str] = None

class CreatorBindingItem(BaseModel):
    creator_id: str
    split_percentage: int = Field(default=70, ge=1, le=99)
    custom_code: Optional[str] = None

class BindCreatorsRequest(BaseModel):
    creator_bindings: List[CreatorBindingItem]

@router.get("/stages")
def list_pipeline_stages():
    """Lists the 13 defined pipeline stages in strict sequential order."""
    return {"stages": STAGE_METADATA, "total": len(STAGE_METADATA)}

@router.post("/deals", status_code=status.HTTP_201_CREATED)
def create_deal(
    payload: CreateDealRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    deal = PartnershipService.create_deal(
        db=db,
        tenant_id=tenant.id,
        creator_id=payload.creator_id,
        title=payload.title,
        product_id=payload.product_id,
        stage=payload.stage,
        creator_split_percentage=payload.creator_split_percentage,
        deal_value_estimate=payload.deal_value_estimate,
        custom_notes=payload.custom_notes,
        created_by=current_user.email
    )
    return {
        "id": deal.id,
        "tenant_id": deal.tenant_id,
        "creator_id": deal.creator_id,
        "product_id": deal.product_id,
        "title": deal.title,
        "stage": deal.stage,
        "creator_split_percentage": deal.creator_split_percentage,
        "platform_split_percentage": deal.platform_split_percentage,
        "deal_value_estimate": deal.deal_value_estimate,
        "referral_code": deal.referral_code,
        "contract_agreement_terms": deal.contract_agreement_terms,
        "created_at": deal.created_at
    }

@router.get("/deals")
def list_deals(
    stage: Optional[str] = None,
    creator_id: Optional[str] = None,
    product_id: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    query = db.query(PartnershipDeal).filter(PartnershipDeal.tenant_id == tenant.id)
    if stage:
        query = query.filter(PartnershipDeal.stage == stage)
    if creator_id:
        query = query.filter(PartnershipDeal.creator_id == creator_id)
    if product_id:
        query = query.filter(PartnershipDeal.product_id == product_id)
    
    deals = query.order_by(PartnershipDeal.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "creator_id": d.creator_id,
            "product_id": d.product_id,
            "title": d.title,
            "stage": d.stage,
            "creator_split_percentage": d.creator_split_percentage,
            "platform_split_percentage": d.platform_split_percentage,
            "deal_value_estimate": d.deal_value_estimate,
            "referral_code": d.referral_code,
            "created_at": d.created_at
        }
        for d in deals
    ]

@router.get("/deals/{deal_id}")
def get_deal(
    deal_id: str,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    deal = db.query(PartnershipDeal).filter(
        PartnershipDeal.id == deal_id,
        PartnershipDeal.tenant_id == tenant.id
    ).first()
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    return {
        "id": deal.id,
        "tenant_id": deal.tenant_id,
        "creator_id": deal.creator_id,
        "product_id": deal.product_id,
        "title": deal.title,
        "stage": deal.stage,
        "creator_split_percentage": deal.creator_split_percentage,
        "platform_split_percentage": deal.platform_split_percentage,
        "deal_value_estimate": deal.deal_value_estimate,
        "referral_code": deal.referral_code,
        "contract_agreement_terms": deal.contract_agreement_terms,
        "created_at": deal.created_at,
        "stage_history": [
            {
                "id": h.id,
                "from_stage": h.from_stage,
                "to_stage": h.to_stage,
                "notes": h.notes,
                "transitioned_by": h.transitioned_by,
                "created_at": h.created_at
            }
            for h in deal.stage_histories
        ],
        "referral_links": [
            {
                "id": rl.id,
                "referral_code": rl.referral_code,
                "attribution_token": rl.attribution_token,
                "clicks_count": rl.clicks_count,
                "conversions_count": rl.conversions_count,
                "total_revenue_generated": rl.total_revenue_generated,
                "is_active": rl.is_active
            }
            for rl in deal.referral_links
        ]
    }

@router.patch("/deals/{deal_id}/stage")
def transition_deal_stage(
    deal_id: str,
    payload: TransitionStageRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    deal = PartnershipService.transition_stage(
        db=db,
        tenant_id=tenant.id,
        deal_id=deal_id,
        to_stage=payload.to_stage,
        notes=payload.notes,
        transitioned_by=current_user.email
    )
    return {
        "id": deal.id,
        "stage": deal.stage,
        "contract_agreement_terms": deal.contract_agreement_terms,
        "updated_at": deal.updated_at
    }

@router.post("/products/{product_id}/bind-creators", status_code=status.HTTP_201_CREATED)
def bind_multiple_creators_to_product(
    product_id: str,
    payload: BindCreatorsRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    bindings_dict = [b.dict() for b in payload.creator_bindings]
    results = PartnershipService.bind_multiple_creators_to_product(
        db=db,
        tenant_id=tenant.id,
        product_id=product_id,
        creator_bindings=bindings_dict,
        created_by=current_user.email
    )
    return {"product_id": product_id, "bound_creators": results, "total_bound": len(results)}

@router.post("/referrals/{referral_code}/click")
def track_referral_click(
    referral_code: str,
    db: Session = Depends(get_db)
):
    link = PartnershipService.record_click(db, referral_code)
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral link not found or inactive")
    return {"status": "success", "referral_code": referral_code, "clicks_count": link.clicks_count}

@router.get("/referrals/{referral_code}/stats")
def get_referral_stats(
    referral_code: str,
    db: Session = Depends(get_db)
):
    link = db.query(CreatorReferralLink).filter(
        CreatorReferralLink.referral_code == referral_code.lower().strip()
    ).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral link not found")
    return {
        "referral_code": link.referral_code,
        "attribution_token": link.attribution_token,
        "clicks_count": link.clicks_count,
        "conversions_count": link.conversions_count,
        "total_revenue_generated_cents": link.total_revenue_generated,
        "is_active": link.is_active
    }

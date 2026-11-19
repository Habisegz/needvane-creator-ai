from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from apps.api.src.core.database import get_db, set_tenant_session
from apps.api.src.api.deps import get_current_user, get_current_tenant
from apps.api.src.models.user import User
from apps.api.src.models.tenant import Organization
from apps.api.src.models.creator import Creator
from apps.api.src.models.product import Product
from apps.api.src.models.email_campaign import EmailCampaign, EmailDispatch
from apps.api.src.models.commerce import Order, CommissionLedger, OrderStatus
from apps.api.src.models.billing import SubscriptionPlan, TenantSubscription, UsageQuota
from apps.api.src.services.billing.subscription_service import SubscriptionService, DEFAULT_PLANS

router = APIRouter(tags=["Subscriptions, Billing & Platform Admin"])

class UpgradePlanRequest(BaseModel):
    new_plan_id: str

@router.get("/billing/plans")
def list_plans(db: Session = Depends(get_db)):
    """Lists available NeedVane SaaS subscription plans."""
    SubscriptionService.seed_plans(db)
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    return [
        {
            "plan_id": p.plan_id,
            "name": p.name,
            "price_monthly_cents": p.price_monthly_cents,
            "creator_monitoring_quota": p.creator_monitoring_quota,
            "product_studio_monthly_quota": p.product_studio_monthly_quota,
            "email_dispatch_monthly_quota": p.email_dispatch_monthly_quota,
            "features": p.features
        }
        for p in plans
    ]

@router.get("/billing/subscription")
def get_subscription_details(
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    sub = SubscriptionService.get_or_create_subscription(db, tenant.id)
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_id == sub.plan_id).first()
    quotas = db.query(UsageQuota).filter(UsageQuota.tenant_id == tenant.id).all()

    return {
        "tenant_id": tenant.id,
        "organization_name": tenant.name,
        "plan_id": sub.plan_id,
        "plan_name": plan.name if plan else sub.plan_id,
        "status": sub.status,
        "current_period_start": sub.current_period_start,
        "current_period_end": sub.current_period_end,
        "quotas": [
            {
                "metric": q.metric_name,
                "current_usage": q.current_usage,
                "limit": q.quota_limit,
                "reset_at": q.reset_at
            }
            for q in quotas
        ]
    }

@router.post("/billing/upgrade")
def upgrade_subscription(
    payload: UpgradePlanRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    sub = SubscriptionService.upgrade_plan(db, tenant_id=tenant.id, new_plan_id=payload.new_plan_id)
    return {
        "status": "success",
        "tenant_id": tenant.id,
        "new_plan_id": sub.plan_id,
        "period_end": sub.current_period_end
    }

@router.get("/admin/overview")
def get_platform_admin_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Platform executive intelligence summary:
    GMV, creator disbursements, total products, active outreach campaigns.
    """
    total_gmv_cents = db.query(func.coalesce(func.sum(Order.total_amount_cents), 0)).filter(
        Order.status == OrderStatus.PAID.value
    ).scalar()

    creator_disbursements_cents = db.query(func.coalesce(func.sum(CommissionLedger.amount_cents), 0)).filter(
        CommissionLedger.entry_type == "creator_credit"
    ).scalar()

    platform_retained_cents = db.query(func.coalesce(func.sum(CommissionLedger.amount_cents), 0)).filter(
        CommissionLedger.entry_type == "platform_fee"
    ).scalar()

    total_creators = db.query(Creator).count()
    total_products = db.query(Product).count()
    total_published_products = db.query(Product).filter(Product.is_published == True).count()
    total_campaigns = db.query(EmailCampaign).count()
    total_dispatches = db.query(EmailDispatch).count()
    total_dispatched_sent = db.query(EmailDispatch).filter(EmailDispatch.status == "sent").count()

    return {
        "platform_name": "NeedVane Creator AI",
        "financials": {
            "gross_merchandise_value_cents": total_gmv_cents,
            "creator_earnings_disbursed_cents": creator_disbursements_cents,
            "platform_net_revenue_cents": platform_retained_cents,
            "currency_standard": "USD"
        },
        "creator_network": {
            "total_monitored_creators": total_creators
        },
        "digital_product_studio": {
            "total_publications_generated": total_products,
            "published_live_storefronts": total_published_products
        },
        "campaign_automation": {
            "total_outreach_campaigns": total_campaigns,
            "total_email_dispatches": total_dispatches,
            "dispatches_completed": total_dispatched_sent
        }
    }

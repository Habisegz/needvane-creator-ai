from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from apps.api.src.models.billing import (
    SubscriptionPlan,
    TenantSubscription,
    UsageQuota,
    PlanTier,
    SubscriptionStatus
)

DEFAULT_PLANS = [
    {
        "plan_id": PlanTier.STARTER.value,
        "name": "NeedVane Starter",
        "price_monthly_cents": 4900,
        "creator_monitoring_quota": 5,
        "product_studio_monthly_quota": 2,
        "email_dispatch_monthly_quota": 250,
        "features": ["Creator Lookalike Discovery", "A4 PDF Generation (Standard)", "Lemon Squeezy Checkout", "Manual CRM"]
    },
    {
        "plan_id": PlanTier.PRO.value,
        "name": "NeedVane Professional",
        "price_monthly_cents": 14900,
        "creator_monitoring_quota": 25,
        "product_studio_monthly_quota": 10,
        "email_dispatch_monthly_quota": 1500,
        "features": ["All Starter Features", "Automated 4-Step Email Sequences", "Multi-Creator Split Binding", "Bonus Pack Generator (A & B)", "Real-time Drift Alerts"]
    },
    {
        "plan_id": PlanTier.ENTERPRISE.value,
        "name": "NeedVane Enterprise Scale",
        "price_monthly_cents": 49900,
        "creator_monitoring_quota": 150,
        "product_studio_monthly_quota": 50,
        "email_dispatch_monthly_quota": 10000,
        "features": ["All Pro Features", "Priority Worker Queues", "Dedicated Partner Manager", "Custom Co-Creation Terms", "Custom Gateway Webhooks"]
    }
]

class SubscriptionService:
    @staticmethod
    def seed_plans(db: Session) -> List[SubscriptionPlan]:
        created = []
        for p in DEFAULT_PLANS:
            plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_id == p["plan_id"]).first()
            if not plan:
                plan = SubscriptionPlan(
                    plan_id=p["plan_id"],
                    name=p["name"],
                    price_monthly_cents=p["price_monthly_cents"],
                    creator_monitoring_quota=p["creator_monitoring_quota"],
                    product_studio_monthly_quota=p["product_studio_monthly_quota"],
                    email_dispatch_monthly_quota=p["email_dispatch_monthly_quota"],
                    features=p["features"]
                )
                db.add(plan)
                created.append(plan)
        if created:
            db.commit()
        return created

    @staticmethod
    def get_or_create_subscription(db: Session, tenant_id: str) -> TenantSubscription:
        sub = db.query(TenantSubscription).filter(TenantSubscription.tenant_id == tenant_id).first()
        if not sub:
            now = datetime.now(timezone.utc)
            sub = TenantSubscription(
                tenant_id=tenant_id,
                plan_id=PlanTier.STARTER.value,
                status=SubscriptionStatus.ACTIVE.value,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                cancel_at_period_end=False
            )
            db.add(sub)
            db.commit()
            db.refresh(sub)
        return sub

    @staticmethod
    def check_quota(db: Session, tenant_id: str, metric_name: str, increment: int = 1) -> bool:
        sub = SubscriptionService.get_or_create_subscription(db, tenant_id)
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_id == sub.plan_id).first()
        
        # Determine limit from plan
        limit = 10
        if plan:
            if metric_name == "monitored_creators":
                limit = plan.creator_monitoring_quota
            elif metric_name == "products_generated":
                limit = plan.product_studio_monthly_quota
            elif metric_name == "email_dispatches":
                limit = plan.email_dispatch_monthly_quota

        quota = db.query(UsageQuota).filter(
            UsageQuota.tenant_id == tenant_id,
            UsageQuota.metric_name == metric_name
        ).first()

        now = datetime.now(timezone.utc)
        if not quota:
            quota = UsageQuota(
                tenant_id=tenant_id,
                metric_name=metric_name,
                current_usage=0,
                quota_limit=limit,
                reset_at=now + timedelta(days=30)
            )
            db.add(quota)
            db.commit()
            db.refresh(quota)
        elif quota.reset_at < now:
            quota.current_usage = 0
            quota.quota_limit = limit
            quota.reset_at = now + timedelta(days=30)
            db.commit()
            db.refresh(quota)

        if quota.current_usage + increment > quota.quota_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Subscription quota exceeded for '{metric_name}' (Current: {quota.current_usage}/{quota.quota_limit}). Please upgrade your NeedVane plan."
            )
        return True

    @staticmethod
    def increment_quota(db: Session, tenant_id: str, metric_name: str, increment: int = 1):
        SubscriptionService.check_quota(db, tenant_id, metric_name, increment)
        quota = db.query(UsageQuota).filter(
            UsageQuota.tenant_id == tenant_id,
            UsageQuota.metric_name == metric_name
        ).first()
        if quota:
            quota.current_usage += increment
            db.commit()

    @staticmethod
    def upgrade_plan(db: Session, tenant_id: str, new_plan_id: str) -> TenantSubscription:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_id == new_plan_id).first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan '{new_plan_id}' not found")

        sub = SubscriptionService.get_or_create_subscription(db, tenant_id)
        sub.plan_id = new_plan_id
        sub.status = SubscriptionStatus.ACTIVE.value
        now = datetime.now(timezone.utc)
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=30)

        # Update quota limits
        quotas = db.query(UsageQuota).filter(UsageQuota.tenant_id == tenant_id).all()
        for q in quotas:
            if q.metric_name == "monitored_creators":
                q.quota_limit = plan.creator_monitoring_quota
            elif q.metric_name == "products_generated":
                q.quota_limit = plan.product_studio_monthly_quota
            elif q.metric_name == "email_dispatches":
                q.quota_limit = plan.email_dispatch_monthly_quota

        db.commit()
        db.refresh(sub)
        return sub

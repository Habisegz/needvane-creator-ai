from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class PlanTier(str, Enum):
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"

class SubscriptionPlan(BaseModel):
    __tablename__ = "subscription_plans"

    plan_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    price_monthly_cents = Column(Integer, nullable=False)
    creator_monitoring_quota = Column(Integer, default=5, nullable=False)
    product_studio_monthly_quota = Column(Integer, default=2, nullable=False)
    email_dispatch_monthly_quota = Column(Integer, default=100, nullable=False)
    features = Column(JSONB, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

class TenantSubscription(BaseModel):
    __tablename__ = "tenant_subscriptions"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    plan_id = Column(String(50), ForeignKey("subscription_plans.plan_id", ondelete="RESTRICT"), nullable=False, index=True)
    status = Column(String(50), default=SubscriptionStatus.ACTIVE.value, nullable=False, index=True)
    current_period_start = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)

    plan = relationship("SubscriptionPlan")

class UsageQuota(BaseModel):
    __tablename__ = "usage_quotas"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)  # monitored_creators, products_generated, email_dispatches
    current_usage = Column(Integer, default=0, nullable=False)
    quota_limit = Column(Integer, default=10, nullable=False)
    reset_at = Column(DateTime(timezone=True), nullable=False)

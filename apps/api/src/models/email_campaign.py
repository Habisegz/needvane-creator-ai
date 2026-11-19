from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from apps.api.src.models.base import BaseModel

class TemplateType(str, enum.Enum):
    OUTREACH = "outreach"
    FOLLOW_UP = "follow_up"
    AFFILIATE_PITCH = "affiliate_pitch"
    CONFIRMATION = "confirmation"

class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class DispatchStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    REPLIED = "replied"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    CANCELLED = "cancelled"

class EmailTemplate(BaseModel):
    __tablename__ = "email_templates"

    tenant_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    template_type = Column(String(50), default="outreach", nullable=False)
    subject_template = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    tags = Column(JSONB, default=list, nullable=False)

class EmailCampaign(BaseModel):
    __tablename__ = "email_campaigns"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="draft", nullable=False)
    sender_name = Column(String(255), default="NeedVane Partnerships", nullable=False)
    sender_email = Column(String(255), nullable=False)
    target_split_percentage = Column(Integer, default=70, nullable=True)
    
    # Sequences relationship
    sequences = relationship("CampaignSequence", back_populates="campaign", cascade="all, delete-orphan", order_by="CampaignSequence.step_number")

class CampaignSequence(BaseModel):
    __tablename__ = "campaign_sequences"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(String(36), ForeignKey("email_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)  # 1 (Day 1), 2 (Day 3), 3 (Day 7), 4 (Day 12)
    delay_days = Column(Integer, default=0, nullable=False)
    subject_template = Column(String(500), nullable=False)
    body_template = Column(Text, nullable=False)

    campaign = relationship("EmailCampaign", back_populates="sequences")

class EmailDispatch(BaseModel):
    __tablename__ = "email_dispatches"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(String(36), ForeignKey("email_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_id = Column(String(36), ForeignKey("campaign_sequences.id", ondelete="SET NULL"), nullable=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    status = Column(String(50), default="queued", nullable=False, index=True)  # queued, sent, replied, bounced, unsubscribed, cancelled
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    reply_received_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(255), nullable=True)

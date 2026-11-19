from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class DealStage(str, Enum):
    DISCOVERED = "discovered"
    RESEARCHED = "researched"
    CONTACT_IDENTIFIED = "contact_identified"
    EMAIL_DRAFTED = "email_drafted"
    AWAITING_APPROVAL = "awaiting_approval"
    PROPOSAL_SENT = "proposal_sent"
    FOLLOW_UP_REQUIRED = "follow_up_required"
    INTERESTED = "interested"
    NEGOTIATION = "negotiation"
    PARTNERSHIP_APPROVED = "partnership_approved"
    PRODUCT_LAUNCHED = "product_launched"
    ACTIVE_PARTNERSHIP = "active_partnership"
    CLOSED_INACTIVE = "closed_inactive"

class PartnershipDeal(BaseModel):
    __tablename__ = "partnership_deals"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    stage = Column(String(50), default=DealStage.DISCOVERED.value, nullable=False, index=True)
    creator_split_percentage = Column(Integer, default=70, nullable=False)
    platform_split_percentage = Column(Integer, default=30, nullable=False)
    deal_value_estimate = Column(Integer, default=0, nullable=False)  # in cents
    target_launch_date = Column(DateTime(timezone=True), nullable=True)
    contract_agreement_terms = Column(Text, nullable=True)
    custom_notes = Column(Text, nullable=True)
    referral_code = Column(String(100), nullable=True)

    stage_histories = relationship(
        "DealStageHistory",
        back_populates="deal",
        cascade="all, delete-orphan",
        order_by="DealStageHistory.created_at.desc()"
    )
    referral_links = relationship(
        "CreatorReferralLink",
        back_populates="deal",
        cascade="all, delete-orphan"
    )

class DealStageHistory(BaseModel):
    __tablename__ = "deal_stage_histories"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    deal_id = Column(String(36), ForeignKey("partnership_deals.id", ondelete="CASCADE"), nullable=False, index=True)
    from_stage = Column(String(50), nullable=True)
    to_stage = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    transitioned_by = Column(String(100), default="system", nullable=False)

    deal = relationship("PartnershipDeal", back_populates="stage_histories")

class CreatorReferralLink(BaseModel):
    __tablename__ = "creator_referral_links"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="CASCADE"), nullable=False, index=True)
    deal_id = Column(String(36), ForeignKey("partnership_deals.id", ondelete="CASCADE"), nullable=True, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    referral_code = Column(String(100), nullable=False, index=True)
    attribution_token = Column(String(64), nullable=False, unique=True, index=True)
    clicks_count = Column(Integer, default=0, nullable=False)
    conversions_count = Column(Integer, default=0, nullable=False)
    total_revenue_generated = Column(Integer, default=0, nullable=False)  # in cents
    is_active = Column(Boolean, default=True, nullable=False)

    deal = relationship("PartnershipDeal", back_populates="referral_links")

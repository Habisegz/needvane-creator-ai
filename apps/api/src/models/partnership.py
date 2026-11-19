from sqlalchemy import Column, String, Integer, BigInteger, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class PartnershipAgreement(BaseModel):
    __tablename__ = "partnership_agreements"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), nullable=True, index=True)  # Tied digital product
    referral_code = Column(String(50), unique=True, nullable=False, index=True)
    creator_rev_share_percent = Column(Numeric(5, 2), default=30.00, nullable=False)
    platform_rev_share_percent = Column(Numeric(5, 2), default=70.00, nullable=False)
    tracking_clicks_count = Column(Integer, default=0, nullable=False)
    total_sales_count = Column(Integer, default=0, nullable=False)
    total_creator_earnings = Column(BigInteger, default=0, nullable=False)  # in minor currency units (kobo/cents)
    status = Column(String(50), default="active", nullable=False)  # active, draft, completed, paused

    # Relationship
    creator = relationship("Creator", back_populates="agreements")

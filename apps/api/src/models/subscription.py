from sqlalchemy import Column, String, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class Subscription(BaseModel):
    __tablename__ = "subscriptions"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), default="paystack", nullable=False)
    external_sub_id = Column(String(255), unique=True, nullable=True)
    status = Column(String(50), default="active", nullable=False)  # active, past_due, canceled
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    monthly_product_quota = Column(Integer, default=2, nullable=False)
    monthly_image_quota = Column(Integer, default=40, nullable=False)
    monthly_email_quota = Column(Integer, default=1000, nullable=False)

    # Relationship
    organization = relationship("Organization", back_populates="subscriptions")

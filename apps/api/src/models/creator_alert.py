from sqlalchemy import Column, String, Boolean, Text, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class CreatorAlert(BaseModel):
    __tablename__ = "creator_alerts"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # new_relevant_post, theme_shift, recurring_problem_spike, new_problem_emerged, source_unavailable
    severity = Column(String(20), default="info", nullable=False)  # info, warning, critical
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, default=dict, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    creator = relationship("Creator", back_populates="alerts")

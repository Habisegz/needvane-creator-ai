from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class CreatorMonitoringLog(BaseModel):
    __tablename__ = "creator_monitoring_logs"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="CASCADE"), nullable=False, index=True)
    checked_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="success", nullable=False)  # success, error, source_unavailable
    posts_checked = Column(Integer, default=0, nullable=False)
    new_posts_count = Column(Integer, default=0, nullable=False)
    changes_detected = Column(Boolean, default=False, nullable=False)
    summary = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    creator = relationship("Creator", back_populates="monitoring_logs")

from sqlalchemy import Column, String, Integer, Numeric, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class Creator(BaseModel):
    __tablename__ = "creators"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # instagram, youtube, tiktok, etc.
    username = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    profile_url = Column(String(500), nullable=False)
    follower_count = Column(Integer, default=0, nullable=False)
    engagement_rate = Column(Numeric(5, 2), default=0.00, nullable=False)
    niche_categories = Column(JSON, default=list, nullable=False)  # e.g. ["fitness", "intermittent_fasting"]
    niche_embedding = Column(JSON, nullable=True)  # Vector representation for kindred lookalike search
    data_tier = Column(String(10), default="Tier C", nullable=False)  # Tier A, Tier B, Tier C, Tier D
    
    # Monitoring Configuration & State
    monitoring_status = Column(String(50), default="active", nullable=False)  # active, paused, unmonitored
    monitoring_interval = Column(String(50), default="daily", nullable=False)  # one-time, daily, weekly, custom
    custom_interval_hours = Column(Integer, default=24, nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    next_check_due = Column(DateTime(timezone=True), nullable=True)
    content_fingerprint = Column(String(64), nullable=True)  # SHA-256 fingerprint of current feed state
    theme_summary = Column(JSON, default=list, nullable=False)  # Detected themes & pain points
    theme_embedding = Column(JSON, nullable=True)  # Vector representation of content themes
    alert_preferences = Column(JSON, default=dict, nullable=False)  # User notification toggles
    
    public_business_email = Column(String(255), nullable=True)

    # Relationships
    agreements = relationship("PartnershipAgreement", back_populates="creator", cascade="all, delete-orphan")
    posts = relationship("CreatorPost", back_populates="creator", cascade="all, delete-orphan")
    monitoring_logs = relationship("CreatorMonitoringLog", back_populates="creator", cascade="all, delete-orphan")
    alerts = relationship("CreatorAlert", back_populates="creator", cascade="all, delete-orphan")

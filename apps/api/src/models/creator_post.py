from sqlalchemy import Column, String, Text, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class CreatorPost(BaseModel):
    __tablename__ = "creator_posts"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="CASCADE"), nullable=False, index=True)
    external_post_id = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)
    caption = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash for deduplication
    detected_topics = Column(JSON, default=list, nullable=False)
    recurring_problems = Column(JSON, default=list, nullable=False)
    posted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    creator = relationship("Creator", back_populates="posts")

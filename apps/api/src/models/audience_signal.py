from sqlalchemy import Column, String, Integer, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class AudienceSignal(BaseModel):
    __tablename__ = "audience_signals"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="SET NULL"), nullable=True, index=True)
    post_id = Column(String(36), ForeignKey("creator_posts.id", ondelete="SET NULL"), nullable=True, index=True)
    
    raw_text = Column(Text, nullable=False)
    signal_type = Column(String(50), default="complaint", nullable=False)  # complaint, question, willingness_to_pay, gap, praise
    sentiment_score = Column(Float, default=0.0, nullable=False)  # -1.0 to +1.0
    evidence_mode = Column(String(50), default="observed", nullable=False)  # observed (direct evidence) vs interpreted (AI synthesis)
    frequency_weight = Column(Integer, default=1, nullable=False)
    embedding = Column(JSON, nullable=True)  # vector representation for semantic clustering

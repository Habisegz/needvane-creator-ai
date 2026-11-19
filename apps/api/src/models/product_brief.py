from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class ProductBrief(BaseModel):
    __tablename__ = "product_briefs"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    unmet_demand_id = Column(String(36), ForeignKey("unmet_demands.id", ondelete="SET NULL"), nullable=True, index=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="SET NULL"), nullable=True, index=True)
    
    title = Column(String(255), nullable=False)
    target_audience = Column(String(255), nullable=False)
    pain_point = Column(Text, nullable=False)
    desired_outcome = Column(Text, nullable=False)
    evidence_mode = Column(String(50), default="verified_research_mapped", nullable=False)
    suggested_format = Column(String(100), default="35-40 Page A4 Publication-Ready PDF + 2 Action Bonuses", nullable=False)
    page_target_min = Column(Integer, default=35, nullable=False)
    page_target_max = Column(Integer, default=40, nullable=False)
    status = Column(String(50), default="ready_for_studio", nullable=False)  # draft, approved, ready_for_studio, in_studio

    # Relationship
    unmet_demand = relationship("UnmetDemand", back_populates="brief")

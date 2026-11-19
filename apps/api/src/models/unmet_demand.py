from sqlalchemy import Column, String, Integer, Numeric, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class UnmetDemand(BaseModel):
    __tablename__ = "unmet_demands"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="SET NULL"), nullable=True, index=True)
    
    title = Column(String(255), nullable=False)
    target_audience = Column(String(255), nullable=False)
    core_problem = Column(Text, nullable=False)
    why_it_matters = Column(Text, nullable=False)
    supporting_evidence = Column(JSON, default=list, nullable=False)  # List of direct observed quotes/citations
    frequency_count = Column(Integer, default=1, nullable=False)
    relevant_questions = Column(JSON, default=list, nullable=False)
    existing_solutions = Column(Text, nullable=False)
    missing_solutions = Column(Text, nullable=False)
    possible_digital_products = Column(JSON, default=list, nullable=False)
    commercial_opportunity = Column(Text, nullable=False)
    
    # 5 Weighted Radar Factor Breakdown
    factor_scores = Column(JSON, default=dict, nullable=False)
    total_radar_score = Column(Numeric(5, 2), default=0.00, nullable=False)
    confidence_level = Column(String(20), default="medium", nullable=False)  # high, medium, low
    
    suggested_product_type = Column(String(100), default="guide_book", nullable=False)
    suggested_format = Column(String(100), default="35-40 Page A4 Publication-Ready PDF + 2 Action Bonuses", nullable=False)
    suggested_price_range = Column(String(50), default="$47 - $97", nullable=False)
    disclaimer = Column(
        Text,
        default="Radar scores reflect heuristic evidence analysis and are never sales predictions.",
        nullable=False
    )
    converted_to_brief_id = Column(String(36), nullable=True)

    # Relationship
    brief = relationship("ProductBrief", back_populates="unmet_demand", uselist=False)

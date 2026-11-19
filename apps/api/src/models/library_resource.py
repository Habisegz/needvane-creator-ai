from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime
from apps.api.src.models.base import BaseModel

class LibraryResource(BaseModel):
    __tablename__ = "library_resources"

    name = Column(String(255), nullable=False, index=True)
    official_website = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    available_content = Column(Text, nullable=False)
    
    # API & Search
    api_available = Column(Boolean, default=False, nullable=False)
    api_documentation_url = Column(String(500), nullable=True)
    authentication_type = Column(String(100), default="none", nullable=False)  # none, api_key, oauth2, subscription_key
    search_capability = Column(String(100), default="keyword", nullable=False)  # full_text, keyword, doi_lookup, parametric, none
    download_export_options = Column(String(255), default="JSON, CSV", nullable=False)
    bulk_access_restrictions = Column(Text, default="Standard rate limits apply", nullable=False)
    rate_limits = Column(String(255), default="Standard public limits", nullable=False)
    
    # Pricing & Commercial Rights
    is_free = Column(Boolean, default=True, nullable=False)
    pricing_model = Column(String(100), default="Free", nullable=False)  # Free, Freemium, Paid, Open Access
    published_pricing = Column(String(255), default="Free / Open Access", nullable=False)
    commercial_use_allowed = Column(Boolean, default=True, nullable=False, index=True)
    attribution_required = Column(Boolean, default=True, nullable=False)
    attribution_format = Column(Text, nullable=True)
    redistribution_restrictions = Column(Text, default="Permitted with attribution", nullable=False)
    geographic_restrictions = Column(String(255), default="Global / None", nullable=False)
    integration_complexity = Column(String(50), default="Low", nullable=False)  # Low, Medium, High
    recommended_application = Column(Text, nullable=False)
    
    # Evidence & Verification
    evidence_url = Column(String(500), nullable=False)
    verification_date = Column(DateTime(timezone=True), nullable=False)
    verification_status = Column(String(50), default="Verified", nullable=False, index=True)  # Verified, Unverified, Stale
    tier_classification = Column(String(50), default="Tier 1: Direct API", nullable=False, index=True)
    # Tiers: Tier 1: Direct API, Tier 2: Approved Platform Integration, Tier 3: Permitted Manual / Semi-Automated, Tier 4: Reference Only
    integration_status = Column(String(50), default="available", nullable=False)  # integrated, available, manual_only, reference_only
    usage_count = Column(Integer, default=0, nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)

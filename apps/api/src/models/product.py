from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from apps.api.src.models.base import BaseModel

class Product(BaseModel):
    __tablename__ = "products"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    topic = Column(String(255), nullable=False)
    target_audience = Column(String(255), nullable=False)
    category = Column(String(100), default="business", nullable=False)
    price_amount = Column(Integer, default=15000, nullable=False)  # in minor units e.g. NGN 150.00 or 15000 kobo
    currency = Column(String(10), default="NGN", nullable=False)
    international_price_cents = Column(Integer, default=2900, nullable=False)  # USD $29.00
    core_page_count = Column(Integer, default=38, nullable=False)
    bonus_count = Column(Integer, default=2, nullable=False)
    pdf_path = Column(String(500), nullable=True)
    bonus_a_path = Column(String(500), nullable=True)
    bonus_b_path = Column(String(500), nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=True, nullable=False)
    editorial_hook = Column(Text, nullable=True)
    sales_copy = Column(JSONB, default=dict, nullable=False)

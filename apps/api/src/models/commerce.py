from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentGateway(str, Enum):
    PAYSTACK = "paystack"
    LEMON_SQUEEZY = "lemonsqueezy"

class Order(BaseModel):
    __tablename__ = "orders"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    order_number = Column(String(64), unique=True, nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False, index=True)
    currency = Column(String(10), default="USD", nullable=False)
    total_amount_cents = Column(Integer, nullable=False)  # minor currency units
    status = Column(String(50), default=OrderStatus.PENDING.value, nullable=False, index=True)
    gateway = Column(String(50), default=PaymentGateway.LEMON_SQUEEZY.value, nullable=False)
    gateway_order_id = Column(String(255), nullable=True, index=True)
    
    # Creator attribution
    referral_code = Column(String(100), nullable=True, index=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="SET NULL"), nullable=True, index=True)
    creator_split_percentage = Column(Integer, default=70, nullable=False)
    creator_amount_cents = Column(Integer, default=0, nullable=False)
    platform_amount_cents = Column(Integer, default=0, nullable=False)
    extra_metadata = Column(JSONB, default=dict, nullable=False)

    transactions = relationship("PaymentTransaction", back_populates="order", cascade="all, delete-orphan")
    ledger_entries = relationship("CommissionLedger", back_populates="order", cascade="all, delete-orphan")
    download_tokens = relationship("DownloadToken", back_populates="order", cascade="all, delete-orphan")

class PaymentTransaction(BaseModel):
    __tablename__ = "payment_transactions"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    gateway = Column(String(50), nullable=False)
    gateway_reference = Column(String(255), unique=True, nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False)
    status = Column(String(50), nullable=False, index=True)  # success, failed, pending
    raw_payload = Column(JSONB, default=dict, nullable=False)
    processed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    order = relationship("Order", back_populates="transactions")

class CommissionLedger(BaseModel):
    __tablename__ = "commission_ledgers"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String(36), ForeignKey("creators.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_type = Column(String(50), nullable=False)  # creator_credit, platform_fee, payout
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    split_ratio = Column(String(20), default="70/30", nullable=False)
    status = Column(String(50), default="accrued", nullable=False)  # accrued, disbursed, reversed
    notes = Column(Text, nullable=True)

    order = relationship("Order", back_populates="ledger_entries")

class DownloadToken(BaseModel):
    __tablename__ = "download_tokens"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_email = Column(String(255), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    download_count = Column(Integer, default=0, nullable=False)
    max_downloads = Column(Integer, default=5, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    download_links = Column(JSONB, default=dict, nullable=False)

    order = relationship("Order", back_populates="download_tokens")

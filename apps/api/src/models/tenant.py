import enum
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint, Enum, JSON
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class TenantRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    CREATOR_MANAGER = "creator_manager"
    EDITOR = "editor"
    VIEWER = "viewer"

class Organization(BaseModel):
    __tablename__ = "organizations"

    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    plan = Column(String(50), default="starter", nullable=False)
    status = Column(String(50), default="active", nullable=False)
    settings = Column(JSON, default=dict, nullable=False)

    # Relationships
    members = relationship("TenantMember", back_populates="organization", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")

class TenantMember(BaseModel):
    __tablename__ = "tenant_members"

    tenant_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default=TenantRole.OWNER.value, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user_membership"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="memberships")

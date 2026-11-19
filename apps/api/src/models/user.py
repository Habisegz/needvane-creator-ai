from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from apps.api.src.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_platform_admin = Column(Boolean, default=False, nullable=False)

    # Relationships
    memberships = relationship("TenantMember", back_populates="user", cascade="all, delete-orphan")

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from apps.api.src.core.database import get_db, set_tenant_session
from apps.api.src.core.security import get_current_token_payload
from apps.api.src.models.user import User
from apps.api.src.models.tenant import Organization, TenantMember

def get_current_user(
    payload: dict = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
) -> User:
    """Verifies and returns the authenticated user."""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid: missing user identifier"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

def get_current_tenant(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    payload: dict = Depends(get_current_token_payload),
    db: Session = Depends(get_db)
) -> Organization:
    """
    CRITICAL MULTI-TENANT ISOLATION:
    Resolves the active tenant and verifies the user is an authorized member.
    Enforces tenant context on the database session to prevent cross-tenant leaks.
    """
    user_id = payload.get("sub")
    # Prefer header if provided, otherwise fallback to token claim
    target_tenant_id = x_tenant_id or payload.get("tenant_id")
    
    if not target_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active workspace tenant context is required"
        )
        
    # Check membership
    membership = db.query(TenantMember).filter(
        TenantMember.tenant_id == target_tenant_id,
        TenantMember.user_id == user_id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied: You are not a member of this workspace"
        )
        
    organization = db.query(Organization).filter(Organization.id == target_tenant_id).first()
    if not organization or organization.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or inactive"
        )
        
    # Set the PostgreSQL RLS session variable
    set_tenant_session(db, target_tenant_id)
    return organization

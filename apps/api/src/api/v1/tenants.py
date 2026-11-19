import re
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from apps.api.src.core.database import get_db
from apps.api.src.models.user import User
from apps.api.src.models.tenant import Organization, TenantMember, TenantRole
from apps.api.src.schemas.tenant import OrganizationCreate, OrganizationOut
from apps.api.src.api.deps import get_current_user

router = APIRouter(prefix="/workspaces", tags=["Workspaces & Multi-Tenancy"])

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text or "workspace"

@router.get("", response_model=List[OrganizationOut])
def list_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lists all organization workspaces the current user has access to."""
    memberships = db.query(TenantMember).filter(TenantMember.user_id == current_user.id).all()
    tenant_ids = [m.tenant_id for m in memberships]
    orgs = db.query(Organization).filter(Organization.id.in_(tenant_ids)).all()
    return orgs

@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new isolated organization workspace and assigns the creator as OWNER."""
    base_slug = data.slug or slugify(data.name)
    slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    org = Organization(
        name=data.name,
        slug=slug,
        plan="starter",
        status="active"
    )
    db.add(org)
    db.flush()

    membership = TenantMember(
        tenant_id=org.id,
        user_id=current_user.id,
        role=TenantRole.OWNER.value
    )
    db.add(membership)
    db.commit()
    db.refresh(org)
    return org

@router.get("/{workspace_id}", response_model=OrganizationOut)
def get_workspace_details(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    CRITICAL MULTI-TENANT CHECK:
    Fetches workspace details ONLY if the caller is an authorized member.
    Explicitly returns 403 Forbidden to prevent cross-tenant enumeration.
    """
    membership = db.query(TenantMember).filter(
        TenantMember.tenant_id == workspace_id,
        TenantMember.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view or access this workspace"
        )
    
    org = db.query(Organization).filter(Organization.id == workspace_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
        
    return org

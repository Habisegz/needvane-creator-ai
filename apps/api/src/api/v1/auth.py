import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from apps.api.src.core.database import get_db
from apps.api.src.core.security import hash_password, verify_password, create_access_token
from apps.api.src.models.user import User
from apps.api.src.models.tenant import Organization, TenantMember, TenantRole
from apps.api.src.models.subscription import Subscription
from apps.api.src.schemas.auth import UserRegister, UserLogin, Token
from apps.api.src.schemas.user import UserWithTenantsOut
from apps.api.src.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text or "workspace"

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_user(data: UserRegister, db: Session = Depends(get_db)):
    """Registers a new user, creates their initial organization workspace, and issues an access token."""
    existing_user = db.query(User).filter(User.email == data.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists"
        )
    
    # 1. Create User
    new_user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        full_name=data.full_name
    )
    db.add(new_user)
    db.flush()

    # 2. Create Default Workspace
    org_name = data.organization_name or f"{data.full_name or 'Creator'}'s Workspace"
    base_slug = slugify(org_name)
    slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    organization = Organization(
        name=org_name,
        slug=slug,
        plan="starter",
        status="active"
    )
    db.add(organization)
    db.flush()

    # 3. Create Membership as OWNER
    membership = TenantMember(
        tenant_id=organization.id,
        user_id=new_user.id,
        role=TenantRole.OWNER.value
    )
    db.add(membership)

    # 4. Create Default Starter Subscription
    subscription = Subscription(
        tenant_id=organization.id,
        provider="system_default",
        status="active",
        monthly_product_quota=2,
        monthly_image_quota=40,
        monthly_email_quota=1000
    )
    db.add(subscription)
    db.commit()
    db.refresh(new_user)
    db.refresh(organization)

    # Issue JWT token
    token = create_access_token({
        "sub": new_user.id,
        "tenant_id": organization.id,
        "role": TenantRole.OWNER.value,
        "email": new_user.email
    })

    return Token(
        access_token=token,
        token_type="bearer",
        tenant_id=organization.id,
        user_id=new_user.id,
        email=new_user.email
    )

@router.post("/login", response_model=Token)
def login_user(data: UserLogin, db: Session = Depends(get_db)):
    """Authenticates user credentials and returns an access token for their primary workspace."""
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Resolve primary active workspace membership
    membership = db.query(TenantMember).join(Organization).filter(
        TenantMember.user_id == user.id,
        Organization.status == "active"
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no active organization workspaces"
        )
    
    token = create_access_token({
        "sub": user.id,
        "tenant_id": membership.tenant_id,
        "role": membership.role,
        "email": user.email
    })

    return Token(
        access_token=token,
        token_type="bearer",
        tenant_id=membership.tenant_id,
        user_id=user.id,
        email=user.email
    )

@router.get("/me", response_model=UserWithTenantsOut)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns profile information for the authenticated user and their authorized workspaces."""
    memberships = db.query(TenantMember).filter(TenantMember.user_id == current_user.id).all()
    workspaces = []
    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.tenant_id).first()
        if org:
            workspaces.append({
                "tenant_id": org.id,
                "name": org.name,
                "slug": org.slug,
                "role": m.role,
                "plan": org.plan,
                "status": org.status
            })
    
    return UserWithTenantsOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_platform_admin=current_user.is_platform_admin,
        created_at=current_user.created_at,
        workspaces=workspaces
    )

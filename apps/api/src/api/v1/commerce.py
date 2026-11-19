from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session

from apps.api.src.core.database import get_db, set_tenant_session
from apps.api.src.api.deps import get_current_user, get_current_tenant
from apps.api.src.models.user import User
from apps.api.src.models.tenant import Organization
from apps.api.src.models.commerce import OrderStatus, PaymentGateway
from apps.api.src.services.commerce.checkout_service import CheckoutService

router = APIRouter(tags=["Commerce, Marketplace & Creator Splits"])

class CreateOrderRequest(BaseModel):
    product_id: str
    customer_name: str
    customer_email: EmailStr
    gateway: str = Field(default=PaymentGateway.LEMON_SQUEEZY.value)
    currency: str = Field(default="USD")
    referral_code: Optional[str] = None

class WebhookFulfillRequest(BaseModel):
    order_id: str
    gateway_reference: str
    raw_payload: Optional[Dict[str, Any]] = None

# Public Blog-Style Storefront Route
@router.get("/p/{slug}")
def get_public_storefront(
    slug: str,
    ref: Optional[str] = Query(None, alias="ref"),
    db: Session = Depends(get_db)
):
    """
    Renders public blog-style sales page with TOC, bonus stack,
    editorial hook, and multi-creator attribution (?ref=creator_handle).
    """
    return CheckoutService.get_storefront_data(db, slug=slug, ref_code=ref)

@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    payload: CreateOrderRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    order = CheckoutService.create_order(
        db=db,
        tenant_id=tenant.id,
        product_id=payload.product_id,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        gateway=payload.gateway,
        currency=payload.currency,
        referral_code=payload.referral_code
    )
    return {
        "id": order.id,
        "order_number": order.order_number,
        "product_id": order.product_id,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "currency": order.currency,
        "total_amount_cents": order.total_amount_cents,
        "status": order.status,
        "gateway": order.gateway,
        "referral_code": order.referral_code,
        "creator_id": order.creator_id,
        "creator_split_percentage": order.creator_split_percentage,
        "creator_amount_cents": order.creator_amount_cents,
        "platform_amount_cents": order.platform_amount_cents
    }

@router.post("/checkout/paystack/initialize")
def initialize_paystack_checkout(
    payload: CreateOrderRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    order = CheckoutService.create_order(
        db=db,
        tenant_id=tenant.id,
        product_id=payload.product_id,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        gateway=PaymentGateway.PAYSTACK.value,
        currency="NGN",
        referral_code=payload.referral_code
    )
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "gateway": "paystack",
        "checkout_url": f"https://checkout.paystack.com/{order.order_number.lower()}",
        "access_code": f"pstk_acc_{order.id[:12]}",
        "amount": order.total_amount_cents,
        "currency": "NGN"
    }

@router.post("/checkout/lemonsqueezy/initialize")
def initialize_lemonsqueezy_checkout(
    payload: CreateOrderRequest,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    order = CheckoutService.create_order(
        db=db,
        tenant_id=tenant.id,
        product_id=payload.product_id,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        gateway=PaymentGateway.LEMON_SQUEEZY.value,
        currency="USD",
        referral_code=payload.referral_code
    )
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "gateway": "lemonsqueezy",
        "checkout_url": f"https://needvane.lemonsqueezy.com/buy/{order.order_number.lower()}",
        "amount": order.total_amount_cents,
        "currency": "USD",
        "merchant_of_record": True,
        "tax_handling": "automatic_vat_and_sales_tax"
    }

@router.post("/webhooks/paystack")
def paystack_webhook(
    payload: WebhookFulfillRequest,
    x_paystack_signature: Optional[str] = Header(None, alias="x-paystack-signature"),
    db: Session = Depends(get_db)
):
    result = CheckoutService.fulfill_paid_order(
        db=db,
        order_id=payload.order_id,
        gateway_reference=payload.gateway_reference,
        raw_payload=payload.raw_payload or {"event": "charge.success", "ref": payload.gateway_reference}
    )
    return {"status": "success", "fulfillment": result["status"]}

@router.post("/webhooks/lemonsqueezy")
def lemonsqueezy_webhook(
    payload: WebhookFulfillRequest,
    x_signature: Optional[str] = Header(None, alias="x-signature"),
    db: Session = Depends(get_db)
):
    result = CheckoutService.fulfill_paid_order(
        db=db,
        order_id=payload.order_id,
        gateway_reference=payload.gateway_reference,
        raw_payload=payload.raw_payload or {"event": "order_created", "ref": payload.gateway_reference}
    )
    return {"status": "success", "fulfillment": result["status"]}

@router.get("/downloads/{token}")
def access_download(
    token: str,
    db: Session = Depends(get_db)
):
    """Secure post-purchase delivery endpoint with expiring 24h token & 5 download max."""
    return CheckoutService.access_download(db, token_hash=token)

@router.get("/creators/{creator_id}/portal")
def get_creator_portal(
    creator_id: str,
    db: Session = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    set_tenant_session(db, tenant.id)
    return CheckoutService.get_creator_portal(db, creator_id=creator_id, tenant_id=tenant.id)

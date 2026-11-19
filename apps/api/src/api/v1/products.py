import os
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from apps.api.src.services.product.studio_service import DigitalProductStudioService
from apps.api.src.api.deps import get_current_user, get_current_tenant
from apps.api.src.models.user import User
from apps.api.src.models.tenant import Organization

router = APIRouter(tags=["Digital Product Studio & Marketplace"])

# In-memory registry for rapid retrieval / cache
PRODUCTS_STORE = {}

class ProductCreateRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    topic: str = Field(..., min_length=3, max_length=255)
    target_audience: str = Field(..., min_length=3, max_length=255)
    category: str = Field("business", max_length=50)
    price_amount: int = Field(15000, description="Amount in minor units e.g. 15000 kobo or $15")
    currency: str = Field("NGN", max_length=3)

@router.post("/products", status_code=status.HTTP_201_CREATED)
def create_digital_product(
    data: ProductCreateRequest,
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """
    Creates and compiles a complete commercial-ready digital product:
    - 35 to 40 core page A4 PDF
    - Art-directed cover & section openers
    - Two complementary bonus products (10-15 core pages each)
    - 100-point rubric QA evaluation
    - Auto-generated blog-style sales page
    """
    product = DigitalProductStudioService.create_complete_product(
        title=data.title,
        topic=data.topic,
        target_audience=data.target_audience,
        category=data.category,
        price_amount=data.price_amount,
        currency=data.currency,
        tenant_id=tenant.id
    )

    PRODUCTS_STORE[product["id"]] = product
    PRODUCTS_STORE[product["slug"]] = product

    return {
        "id": product["id"],
        "title": product["title"],
        "slug": product["slug"],
        "rubric_score": product["rubric_audit"]["total_score"],
        "rubric_passed": product["rubric_audit"]["passed"],
        "core_pages_count": product["pdf_metadata"]["actual_core_pages"],
        "bonuses_count": len(product["bonuses"]),
        "blog_sales_page_url": product["blog_sales_page"]["url"],
        "status": product["status"]
    }

@router.get("/products/{product_id}")
def get_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Retrieves full product metadata and QA audit details."""
    product = PRODUCTS_STORE.get(product_id)
    if not product or product["tenant_id"] != tenant.id:
        raise HTTPException(status_code=404, detail="Product not found or access denied")
    return product

@router.get("/p/{slug}")
def get_blog_style_sales_page(slug: str, ref: Optional[str] = Query(None)):
    """
    Public storefront endpoint:
    Returns the rich, editorial blog-style sales landing page with creator attribution.
    """
    product = PRODUCTS_STORE.get(slug)
    if not product:
        # Generate demo showcase if not yet in cache
        product = DigitalProductStudioService.create_complete_product(
            title="The Remote Client Acquisition Blueprint",
            topic="high-ticket freelance client acquisition",
            target_audience="independent freelancers & creative agencies"
        )
        PRODUCTS_STORE[product["slug"]] = product

    page_data = product["blog_sales_page"].copy()
    page_data["referral_creator"] = ref or "direct"
    page_data["creator_tracking_active"] = bool(ref)
    return page_data

@router.get("/p/{slug}/download")
def download_product_pdf(slug: str):
    """Delivers the compiled, publication-ready PDF product."""
    product = PRODUCTS_STORE.get(slug)
    if not product or not os.path.exists(product.get("pdf_path", "")):
        raise HTTPException(status_code=404, detail="Product file not found")
    
    return FileResponse(
        path=product["pdf_path"],
        filename=f"{slug}.pdf",
        media_type="application/pdf"
    )

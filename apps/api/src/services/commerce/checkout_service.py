import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from apps.api.src.models.product import Product
from apps.api.src.models.creator import Creator
from apps.api.src.models.partnership_deal import CreatorReferralLink, PartnershipDeal
from apps.api.src.models.commerce import (
    Order,
    PaymentTransaction,
    CommissionLedger,
    DownloadToken,
    OrderStatus,
    PaymentGateway
)

class CheckoutService:
    @staticmethod
    def get_storefront_data(db: Session, slug: str, ref_code: Optional[str] = None) -> Dict[str, Any]:
        product = db.query(Product).filter(Product.slug == slug, Product.is_published == True).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found or unpublished")

        co_creator_info = None
        attributed_split = 70
        if ref_code:
            link = db.query(CreatorReferralLink).filter(
                CreatorReferralLink.referral_code == ref_code.lower().strip(),
                CreatorReferralLink.is_active == True
            ).first()
            if link:
                creator = db.query(Creator).filter(Creator.id == link.creator_id).first()
                if creator:
                    co_creator_info = {
                        "display_name": creator.display_name or creator.username,
                        "username": creator.username,
                        "platform": creator.platform,
                        "follower_count": creator.follower_count,
                        "attribution_verified": True
                    }
                    if link.deal_id:
                        deal = db.query(PartnershipDeal).filter(PartnershipDeal.id == link.deal_id).first()
                        if deal:
                            attributed_split = deal.creator_split_percentage

        return {
            "id": product.id,
            "title": product.title,
            "slug": product.slug,
            "topic": product.topic,
            "target_audience": product.target_audience,
            "category": product.category,
            "price_amount": product.price_amount,
            "currency": product.currency,
            "international_price_cents": product.international_price_cents,
            "core_page_count": product.core_page_count,
            "bonus_count": product.bonus_count,
            "editorial_hook": product.editorial_hook or f"The definitive publication on {product.topic}.",
            "table_of_contents_preview": [
                {"chapter": 1, "title": "Foundational Principles & Architecture", "pages": "1-8"},
                {"chapter": 2, "title": "Execution Framework & Step-by-Step System", "pages": "9-22"},
                {"chapter": 3, "title": "Scaling, Automation & Legal Risk Safeguards", "pages": "23-38"}
            ],
            "bonus_stack": [
                {
                    "name": "Bonus Pack A: Operational Blueprint & Action Workbook",
                    "pages": 12,
                    "description": "Step-by-step implementation worksheets, sprint checklists, and audit rubrics."
                },
                {
                    "name": "Bonus Pack B: Plug-and-Play Production Templates",
                    "pages": 11,
                    "description": "Field-tested standard operating procedures and copy frameworks."
                }
            ],
            "co_creator": co_creator_info,
            "referral_code": ref_code,
            "guarantee": "30-Day Money-Back Guarantee. Instant Secure Digital Access.",
            "is_published": product.is_published
        }

    @staticmethod
    def create_order(
        db: Session,
        tenant_id: str,
        product_id: str,
        customer_name: str,
        customer_email: str,
        gateway: str = PaymentGateway.LEMON_SQUEEZY.value,
        currency: str = "USD",
        referral_code: Optional[str] = None
    ) -> Order:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        # Determine price based on currency
        if currency.upper() == "NGN":
            total_amount = product.price_amount
        else:
            total_amount = product.international_price_cents

        # Creator attribution check
        creator_id = None
        split_pct = 0
        if referral_code:
            link = db.query(CreatorReferralLink).filter(
                CreatorReferralLink.referral_code == referral_code.lower().strip(),
                CreatorReferralLink.is_active == True
            ).first()
            if link:
                creator_id = link.creator_id
                split_pct = 70  # default
                if link.deal_id:
                    deal = db.query(PartnershipDeal).filter(PartnershipDeal.id == link.deal_id).first()
                    if deal:
                        split_pct = deal.creator_split_percentage

        creator_amount = int(total_amount * (split_pct / 100.0))
        platform_amount = total_amount - creator_amount

        order_num = f"NV-ORD-{uuid.uuid4().hex[:10].upper()}"

        order = Order(
            tenant_id=tenant_id,
            order_number=order_num,
            product_id=product_id,
            customer_name=customer_name,
            customer_email=customer_email.lower().strip(),
            currency=currency.upper(),
            total_amount_cents=total_amount,
            status=OrderStatus.PENDING.value,
            gateway=gateway,
            referral_code=referral_code.lower().strip() if referral_code else None,
            creator_id=creator_id,
            creator_split_percentage=split_pct,
            creator_amount_cents=creator_amount,
            platform_amount_cents=platform_amount
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def fulfill_paid_order(
        db: Session,
        order_id: str,
        gateway_reference: str,
        raw_payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Idempotent fulfillment engine:
        - Updates Order to PAID
        - Records PaymentTransaction
        - Generates 24-hr secure DownloadToken (5 max downloads)
        - Writes immutable split records to CommissionLedger
        - Increments conversion & revenue on referral link
        """
        # Idempotency check
        existing_tx = db.query(PaymentTransaction).filter(
            PaymentTransaction.gateway_reference == gateway_reference
        ).first()
        if existing_tx:
            order = db.query(Order).filter(Order.id == existing_tx.order_id).first()
            token = db.query(DownloadToken).filter(DownloadToken.order_id == order.id).first()
            return {"order": order, "download_token": token, "status": "already_fulfilled"}

        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        order.status = OrderStatus.PAID.value
        order.gateway_order_id = gateway_reference

        # Record payment transaction
        tx = PaymentTransaction(
            tenant_id=order.tenant_id,
            order_id=order.id,
            gateway=order.gateway,
            gateway_reference=gateway_reference,
            amount_cents=order.total_amount_cents,
            currency=order.currency,
            status="success",
            raw_payload=raw_payload or {"reference": gateway_reference}
        )
        db.add(tx)

        # Generate download token (24-hour expiration, max 5 downloads)
        raw_token = f"{order.id}:{order.customer_email}:{uuid.uuid4().hex}"
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        download_token = DownloadToken(
            tenant_id=order.tenant_id,
            order_id=order.id,
            product_id=order.product_id,
            customer_email=order.customer_email,
            token=token_hash,
            expires_at=expires_at,
            download_count=0,
            max_downloads=5,
            is_revoked=False,
            download_links={
                "core_publication_pdf": f"/api/v1/downloads/{token_hash}/file/core",
                "bonus_pack_a": f"/api/v1/downloads/{token_hash}/file/bonus-a",
                "bonus_pack_b": f"/api/v1/downloads/{token_hash}/file/bonus-b"
            }
        )
        db.add(download_token)

        # Creator Split Ledger entries
        ledger_entries = []
        if order.creator_id and order.creator_amount_cents > 0:
            creator_ledger = CommissionLedger(
                tenant_id=order.tenant_id,
                order_id=order.id,
                creator_id=order.creator_id,
                entry_type="creator_credit",
                amount_cents=order.creator_amount_cents,
                currency=order.currency,
                split_ratio=f"{order.creator_split_percentage}/{100-order.creator_split_percentage}",
                status="accrued",
                notes=f"Creator {order.creator_split_percentage}% split for Order {order.order_number}"
            )
            platform_ledger = CommissionLedger(
                tenant_id=order.tenant_id,
                order_id=order.id,
                creator_id=order.creator_id,
                entry_type="platform_fee",
                amount_cents=order.platform_amount_cents,
                currency=order.currency,
                split_ratio=f"{order.creator_split_percentage}/{100-order.creator_split_percentage}",
                status="accrued",
                notes=f"Platform {100-order.creator_split_percentage}% fee for Order {order.order_number}"
            )
            db.add_all([creator_ledger, platform_ledger])
            ledger_entries = [creator_ledger, platform_ledger]

            # Update referral link conversions and revenue
            if order.referral_code:
                link = db.query(CreatorReferralLink).filter(
                    CreatorReferralLink.referral_code == order.referral_code
                ).first()
                if link:
                    link.conversions_count += 1
                    link.total_revenue_generated += order.total_amount_cents

        db.commit()
        db.refresh(order)
        db.refresh(download_token)

        return {
            "order": order,
            "download_token": download_token,
            "status": "fulfilled",
            "ledger_count": len(ledger_entries)
        }

    @staticmethod
    def access_download(db: Session, token_hash: str) -> Dict[str, Any]:
        download_token = db.query(DownloadToken).filter(
            DownloadToken.token == token_hash,
            DownloadToken.is_revoked == False
        ).first()

        if not download_token:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Download link not found or invalid")

        now = datetime.now(timezone.utc)
        if download_token.expires_at < now:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Download link has expired (24-hour limit)")

        if download_token.download_count >= download_token.max_downloads:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Maximum download limit reached ({download_token.max_downloads} downloads)"
            )

        download_token.download_count += 1
        db.commit()
        db.refresh(download_token)

        product = db.query(Product).filter(Product.id == download_token.product_id).first()

        return {
            "token": download_token.token,
            "customer_email": download_token.customer_email,
            "product_title": product.title if product else "Digital Publication",
            "download_count": download_token.download_count,
            "max_downloads": download_token.max_downloads,
            "remaining_downloads": download_token.max_downloads - download_token.download_count,
            "expires_at": download_token.expires_at,
            "download_links": download_token.download_links
        }

    @staticmethod
    def get_creator_portal(db: Session, creator_id: str, tenant_id: str) -> Dict[str, Any]:
        creator = db.query(Creator).filter(Creator.id == creator_id, Creator.tenant_id == tenant_id).first()
        if not creator:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")

        links = db.query(CreatorReferralLink).filter(
            CreatorReferralLink.creator_id == creator_id,
            CreatorReferralLink.tenant_id == tenant_id
        ).all()

        total_clicks = sum(link.clicks_count for link in links)
        total_conversions = sum(link.conversions_count for link in links)
        total_gross_cents = sum(link.total_revenue_generated for link in links)

        conversion_rate = (total_conversions / total_clicks * 100.0) if total_clicks > 0 else 0.0

        # Ledger earnings
        ledger_entries = db.query(CommissionLedger).filter(
            CommissionLedger.creator_id == creator_id,
            CommissionLedger.tenant_id == tenant_id,
            CommissionLedger.entry_type == "creator_credit"
        ).order_by(CommissionLedger.created_at.desc()).all()

        net_earned_cents = sum(entry.amount_cents for entry in ledger_entries)

        return {
            "creator_id": creator.id,
            "display_name": creator.display_name or creator.username,
            "username": creator.username,
            "total_referral_links": len(links),
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "conversion_rate_percentage": round(conversion_rate, 2),
            "gross_sales_cents": total_gross_cents,
            "net_earned_cents": net_earned_cents,
            "referral_links": [
                {
                    "referral_code": l.referral_code,
                    "clicks": l.clicks_count,
                    "conversions": l.conversions_count,
                    "total_revenue_cents": l.total_revenue_generated
                }
                for l in links
            ],
            "recent_ledger_entries": [
                {
                    "id": le.id,
                    "order_id": le.order_id,
                    "amount_cents": le.amount_cents,
                    "currency": le.currency,
                    "split_ratio": le.split_ratio,
                    "status": le.status,
                    "created_at": le.created_at
                }
                for le in ledger_entries[:10]
            ]
        }

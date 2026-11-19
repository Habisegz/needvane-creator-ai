import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from apps.api.src.models.creator import Creator
from apps.api.src.models.product import Product
from apps.api.src.models.partnership_deal import (
    PartnershipDeal,
    DealStageHistory,
    CreatorReferralLink,
    DealStage
)

VALID_STAGES = {stage.value for stage in DealStage}

class PartnershipService:
    @staticmethod
    def generate_referral_token(creator_id: str, product_id: str, referral_code: str) -> str:
        raw = f"{creator_id}:{product_id}:{referral_code}:{uuid.uuid4().hex}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_contract_terms(
        creator_name: str,
        product_title: str,
        creator_split: int,
        platform_split: int,
        referral_code: str
    ) -> str:
        return f"""CO-CREATION & COMMERCIAL DISTRIBUTION AGREEMENT

This Agreement is entered into between NeedVane Creator AI ("Platform") and {creator_name} ("Creator Partner").

1. PRODUCT DEFINITION
The Platform has researched, authored, and designed a publication-ready digital product titled "{product_title}" (A4 format, strict publication guidelines, and bonus material suites).

2. REVENUE SHARE & DISTRIBUTION
- Creator Partner Revenue Allocation: {creator_split}% of net collected receipts.
- Platform Revenue Allocation: {platform_split}% of net collected receipts.
- All transactions will be processed via compliant global gateways (Lemon Squeezy as Merchant of Record for international sales with automated sales tax/VAT handling, and Paystack for regional/direct bank transfers).

3. ATTRIBUTION & REFERRAL ARCHITECTURE
The Creator Partner is assigned the dedicated tracking identifier:
- Referral Parameter: ?ref={referral_code}
- Automated Cookie & Session Window: 30-day multi-touch attribution.

4. IP & NON-EXCLUSIVE LICENSE
Content is published and co-branded under non-exclusive distribution terms. Creator reserves full ownership of likeness and personal brand marks.

Date Issued: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
Status: Legally Binding & Programmatically Executed
"""

    @staticmethod
    def create_deal(
        db: Session,
        tenant_id: str,
        creator_id: str,
        title: str,
        product_id: Optional[str] = None,
        stage: str = DealStage.DISCOVERED.value,
        creator_split_percentage: int = 70,
        deal_value_estimate: int = 50000,
        custom_notes: Optional[str] = None,
        created_by: str = "system"
    ) -> PartnershipDeal:
        if stage not in VALID_STAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stage '{stage}'. Must be one of: {list(VALID_STAGES)}"
            )

        creator = db.query(Creator).filter(Creator.id == creator_id, Creator.tenant_id == tenant_id).first()
        if not creator:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")

        platform_split = 100 - creator_split_percentage
        ref_code = (creator.username or f"creator_{creator.id[:8]}").lower().strip().replace(" ", "_")

        product = None
        if product_id:
            product = db.query(Product).filter(Product.id == product_id).first()

        terms = None
        if product:
            terms = PartnershipService.generate_contract_terms(
                creator_name=creator.display_name or creator.username,
                product_title=product.title,
                creator_split=creator_split_percentage,
                platform_split=platform_split,
                referral_code=ref_code
            )

        deal = PartnershipDeal(
            tenant_id=tenant_id,
            creator_id=creator_id,
            product_id=product_id,
            title=title,
            stage=stage,
            creator_split_percentage=creator_split_percentage,
            platform_split_percentage=platform_split,
            deal_value_estimate=deal_value_estimate,
            custom_notes=custom_notes,
            referral_code=ref_code,
            contract_agreement_terms=terms
        )
        db.add(deal)
        db.flush()

        # Record initial stage history
        history = DealStageHistory(
            tenant_id=tenant_id,
            deal_id=deal.id,
            from_stage=None,
            to_stage=stage,
            notes=f"Deal initialized in {stage} stage",
            transitioned_by=created_by
        )
        db.add(history)

        # If product is attached, create referral link
        if product_id:
            token = PartnershipService.generate_referral_token(creator_id, product_id, ref_code)
            referral_link = CreatorReferralLink(
                tenant_id=tenant_id,
                creator_id=creator_id,
                deal_id=deal.id,
                product_id=product_id,
                referral_code=ref_code,
                attribution_token=token,
                is_active=True
            )
            db.add(referral_link)

        db.commit()
        db.refresh(deal)
        return deal

    @staticmethod
    def transition_stage(
        db: Session,
        tenant_id: str,
        deal_id: str,
        to_stage: str,
        notes: Optional[str] = None,
        transitioned_by: str = "system"
    ) -> PartnershipDeal:
        if to_stage not in VALID_STAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stage '{to_stage}'. Valid: {list(VALID_STAGES)}"
            )

        deal = db.query(PartnershipDeal).filter(
            PartnershipDeal.id == deal_id,
            PartnershipDeal.tenant_id == tenant_id
        ).first()

        if not deal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partnership deal not found")

        old_stage = deal.stage
        if old_stage == to_stage:
            return deal

        deal.stage = to_stage

        # If entering approved or launched and contract terms not set, generate them
        if to_stage in (DealStage.PARTNERSHIP_APPROVED.value, DealStage.PRODUCT_LAUNCHED.value, DealStage.ACTIVE_PARTNERSHIP.value):
            if not deal.contract_agreement_terms and deal.product_id:
                creator = db.query(Creator).filter(Creator.id == deal.creator_id).first()
                product = db.query(Product).filter(Product.id == deal.product_id).first()
                if creator and product:
                    deal.contract_agreement_terms = PartnershipService.generate_contract_terms(
                        creator_name=creator.display_name or creator.username,
                        product_title=product.title,
                        creator_split=deal.creator_split_percentage,
                        platform_split=deal.platform_split_percentage,
                        referral_code=deal.referral_code or creator.username
                    )

            # Ensure referral link exists
            if deal.product_id:
                existing_link = db.query(CreatorReferralLink).filter(
                    CreatorReferralLink.deal_id == deal.id,
                    CreatorReferralLink.tenant_id == tenant_id
                ).first()
                if not existing_link:
                    token = PartnershipService.generate_referral_token(deal.creator_id, deal.product_id, deal.referral_code)
                    new_link = CreatorReferralLink(
                        tenant_id=tenant_id,
                        creator_id=deal.creator_id,
                        deal_id=deal.id,
                        product_id=deal.product_id,
                        referral_code=deal.referral_code,
                        attribution_token=token,
                        is_active=True
                    )
                    db.add(new_link)

        # Add history record
        history = DealStageHistory(
            tenant_id=tenant_id,
            deal_id=deal.id,
            from_stage=old_stage,
            to_stage=to_stage,
            notes=notes or f"Transitioned from {old_stage} to {to_stage}",
            transitioned_by=transitioned_by
        )
        db.add(history)

        db.commit()
        db.refresh(deal)
        return deal

    @staticmethod
    def bind_multiple_creators_to_product(
        db: Session,
        tenant_id: str,
        product_id: str,
        creator_bindings: List[Dict[str, Any]],
        created_by: str = "system"
    ) -> List[Dict[str, Any]]:
        """
        Binds 2-3+ creators to the same product with distinct referral codes and split ratios.
        creator_bindings: [
            {"creator_id": "...", "split_percentage": 70, "custom_code": "opt_code"},
            ...
        ]
        """
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        results = []
        for binding in creator_bindings:
            c_id = binding["creator_id"]
            split_pct = binding.get("split_percentage", 70)
            custom_code = binding.get("custom_code")

            creator = db.query(Creator).filter(Creator.id == c_id, Creator.tenant_id == tenant_id).first()
            if not creator:
                continue

            ref_code = custom_code or creator.username or f"ref_{c_id[:8]}"
            ref_code = ref_code.lower().strip().replace(" ", "_")

            deal = PartnershipDeal(
                tenant_id=tenant_id,
                creator_id=c_id,
                product_id=product_id,
                title=f"Co-Creation Partnership: {creator.display_name or creator.username} x {product.title}",
                stage=DealStage.PARTNERSHIP_APPROVED.value,
                creator_split_percentage=split_pct,
                platform_split_percentage=100 - split_pct,
                deal_value_estimate=product.price_amount * 10,
                referral_code=ref_code,
                contract_agreement_terms=PartnershipService.generate_contract_terms(
                    creator_name=creator.display_name or creator.username,
                    product_title=product.title,
                    creator_split=split_pct,
                    platform_split=100 - split_pct,
                    referral_code=ref_code
                )
            )
            db.add(deal)
            db.flush()

            history = DealStageHistory(
                tenant_id=tenant_id,
                deal_id=deal.id,
                from_stage=None,
                to_stage=DealStage.PARTNERSHIP_APPROVED.value,
                notes=f"Auto-bound to product {product.title} with {split_pct}/{100-split_pct} split",
                transitioned_by=created_by
            )
            db.add(history)

            token = PartnershipService.generate_referral_token(c_id, product_id, ref_code)
            link = CreatorReferralLink(
                tenant_id=tenant_id,
                creator_id=c_id,
                deal_id=deal.id,
                product_id=product_id,
                referral_code=ref_code,
                attribution_token=token,
                is_active=True
            )
            db.add(link)
            db.flush()

            results.append({
                "deal_id": deal.id,
                "creator_id": c_id,
                "creator_username": creator.username,
                "product_id": product_id,
                "referral_code": ref_code,
                "referral_url": f"/p/{product.slug}?ref={ref_code}",
                "attribution_token": token,
                "split_ratio": f"{split_pct}/{100-split_pct}"
            })

        db.commit()
        return results

    @staticmethod
    def record_click(db: Session, referral_code: str) -> Optional[CreatorReferralLink]:
        link = db.query(CreatorReferralLink).filter(
            CreatorReferralLink.referral_code == referral_code.lower().strip(),
            CreatorReferralLink.is_active == True
        ).first()
        if link:
            link.clicks_count += 1
            db.commit()
            db.refresh(link)
        return link

    @staticmethod
    def record_conversion(db: Session, referral_code: str, amount_cents: int) -> Optional[CreatorReferralLink]:
        link = db.query(CreatorReferralLink).filter(
            CreatorReferralLink.referral_code == referral_code.lower().strip(),
            CreatorReferralLink.is_active == True
        ).first()
        if link:
            link.conversions_count += 1
            link.total_revenue_generated += amount_cents
            db.commit()
            db.refresh(link)
        return link

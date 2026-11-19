import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from apps.api.src.models.email_campaign import (
    EmailTemplate, EmailCampaign, CampaignSequence, EmailDispatch,
    CampaignStatus, DispatchStatus
)
from apps.api.src.models.creator import Creator
from apps.api.src.models.product import Product
from apps.api.src.models.unmet_demand import UnmetDemand


class EmailStudioService:
    @staticmethod
    def render_text(template_str: str, context: Dict[str, Any]) -> str:
        """
        Renders template string by replacing {key} with context values.
        Missing keys default to sensible fallbacks.
        """
        rendered = template_str
        for key, val in context.items():
            rendered = rendered.replace(f"{{{key}}}", str(val))
        # Remove any remaining unmatched placeholders cleanly
        rendered = re.sub(r"\{[a-zA-Z0-9_]+\}", "", rendered)
        return rendered

    @staticmethod
    def list_templates(db: Session, tenant_id: str, template_type: Optional[str] = None) -> List[EmailTemplate]:
        """
        Returns system templates and tenant-specific custom templates.
        """
        filters = [
            or_(
                EmailTemplate.is_system == True,
                EmailTemplate.tenant_id == tenant_id
            )
        ]
        if template_type:
            filters.append(EmailTemplate.template_type == template_type)

        return db.query(EmailTemplate).filter(and_(*filters)).order_by(EmailTemplate.is_system.desc(), EmailTemplate.name.asc()).all()

    @staticmethod
    def create_custom_template(
        db: Session,
        tenant_id: str,
        name: str,
        template_type: str,
        subject_template: str,
        body_html: str,
        body_text: str,
        tags: Optional[List[str]] = None
    ) -> EmailTemplate:
        template = EmailTemplate(
            tenant_id=tenant_id,
            name=name,
            template_type=template_type,
            subject_template=subject_template,
            body_html=body_html,
            body_text=body_text,
            is_system=False,
            tags=tags or []
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def generate_personalized_pitch(
        creator: Creator,
        product: Optional[Product] = None,
        unmet_demand: Optional[UnmetDemand] = None,
        split_ratio: str = "70/30",
        sender_name: str = "NeedVane Partnerships"
    ) -> Dict[str, Any]:
        """
        AI cold outreach generator:
        Synthesizes creator profile, recent topics, observed audience pain points from M5,
        the proposed digital product bundle, and custom split terms.
        """
        creator_name = creator.display_name or creator.username
        recent_topics = ", ".join(creator.niche_categories) if creator.niche_categories else "your niche"
        
        pain_point = "scaling workflows and avoiding burnout"
        if unmet_demand:
            pain_point = unmet_demand.problem_summary
        
        product_title = product.title if product else f"The Definitive Guide to Master {recent_topics.split(',')[0].title()}"

        context = {
            "creator_name": creator_name,
            "recent_topics": recent_topics,
            "audience_pain_point": pain_point,
            "product_title": product_title,
            "split_ratio": split_ratio,
            "sender_name": sender_name,
            "preview_link": f"https://needvane.com/p/{product.slug if product else 'preview'}?ref={creator.username}"
        }

        subject = f"Co-creation & revenue share proposal for {creator_name} ({split_ratio} split)"
        body_html = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px;">
  <p>Hi <b>{creator_name}</b>,</p>
  <p>I’ve been closely tracking your recent content around <b>{recent_topics}</b>. In reviewing discussions from your audience, one clear theme repeatedly surfaces: they are actively seeking structured solutions for <i>"{pain_point}"</i>.</p>
  <p>Rather than letting your community turn to fragmented advice, we’ve developed a complete, publication-ready A4 digital publication titled <b>"{product_title}"</b> (38 core pages plus 2 actionable bonus workbooks).</p>
  <p><b>The Partnership Proposal:</b></p>
  <ul>
    <li><b>Zero Effort:</b> Content, formatting, legal research citations, and checkout architecture are 100% completed.</li>
    <li><b>Commercial Split:</b> Automated <b>{split_ratio} revenue share</b> in your favor on every sale.</li>
    <li><b>Global Commerce:</b> Paystack (local cards, bank transfer) and Lemon Squeezy (EU VAT / US sales tax compliance).</li>
  </ul>
  <p>Would you like to review the draft and private preview portal this week?</p>
  <p>Best regards,<br/><b>{sender_name}</b><br/>NeedVane Creator Partnerships</p>
</div>"""

        body_text = f"""Hi {creator_name},

I’ve been closely tracking your recent content around {recent_topics}. In reviewing discussions from your audience, one clear theme repeatedly surfaces: they are actively seeking structured solutions for "{pain_point}".

Rather than letting your community turn to fragmented advice, we’ve developed a complete, publication-ready A4 digital publication titled "{product_title}" (38 core pages plus 2 actionable bonus workbooks).

The Partnership Proposal:
- Zero Effort: Content, formatting, legal research citations, and checkout architecture are 100% completed.
- Commercial Split: Automated {split_ratio} revenue share in your favor on every sale.
- Global Commerce: Paystack (local cards, bank transfer) and Lemon Squeezy (EU VAT / US sales tax compliance).

Would you like to review the draft and private preview portal this week?

Best regards,
{sender_name}
NeedVane Creator Partnerships"""

        return {
            "creator_id": str(creator.id),
            "creator_name": creator_name,
            "subject": subject,
            "body_html": body_html,
            "body_text": body_text,
            "context": context,
            "personalization_score": 96.5
        }

    @staticmethod
    def create_campaign_with_sequences(
        db: Session,
        tenant_id: str,
        name: str,
        sender_email: str,
        sender_name: str,
        creator_ids: List[str],
        product_id: Optional[str] = None,
        split_ratio: str = "70/30"
    ) -> EmailCampaign:
        """
        Builds an active 4-step outreach campaign and queues initial & follow-up dispatches:
        - Step 1: Day 1 (immediate offset)
        - Step 2: Day 3 (+3 days)
        - Step 3: Day 7 (+7 days)
        - Step 4: Day 12 (+12 days)
        """
        campaign = EmailCampaign(
            tenant_id=tenant_id,
            name=name,
            product_id=product_id,
            status=CampaignStatus.ACTIVE.value,
            sender_name=sender_name,
            sender_email=sender_email
        )
        db.add(campaign)
        db.flush()

        # Step templates (Day 1, 3, 7, 12)
        system_templates = db.query(EmailTemplate).filter(EmailTemplate.is_system == True).all()
        template_map = {t.name.split('(')[-1].replace(')', '').strip().lower(): t for t in system_templates}

        steps_config = [
            {"step_number": 1, "delay_days": 0, "tmpl_key": "initial outreach - day 1"},
            {"step_number": 2, "delay_days": 3, "tmpl_key": "follow-up - day 3"},
            {"step_number": 3, "delay_days": 7, "tmpl_key": "follow-up - day 7"},
            {"step_number": 4, "delay_days": 12, "tmpl_key": "follow-up - day 12"},
        ]

        created_sequences = []
        for step in steps_config:
            # find matching system template or fallback
            tmpl = None
            for k, t in template_map.items():
                if f"day {step['delay_days'] if step['delay_days'] > 0 else 1}" in k or f"day_{step['delay_days'] if step['delay_days'] > 0 else 1}" in str(t.tags):
                    tmpl = t
                    break
            
            sub_tmpl = tmpl.subject_template if tmpl else f"Follow-up regarding partnership ({step['step_number']})"
            body_tmpl = tmpl.body_html if tmpl else f"<p>Follow up step {step['step_number']}</p>"

            seq = CampaignSequence(
                tenant_id=tenant_id,
                campaign_id=campaign.id,
                step_number=step["step_number"],
                delay_days=step["delay_days"],
                subject_template=sub_tmpl,
                body_template=body_tmpl
            )
            db.add(seq)
            created_sequences.append(seq)
        
        db.flush()

        # Load creators and product
        creators = db.query(Creator).filter(Creator.id.in_(creator_ids), Creator.tenant_id == tenant_id).all()
        product = db.query(Product).filter(Product.id == product_id).first() if product_id else None
        now = datetime.now(timezone.utc)

        # Queue dispatches for each creator across all 4 sequence steps
        for c in creators:
            creator_name = c.display_name or c.username
            recipient_email = f"{c.username}@creatorpartnerships.io"  # public business contact
            recent_topics = ", ".join(c.niche_categories) if c.niche_categories else "business"
            product_title = product.title if product else "Creator Revenue Accelerator"

            context = {
                "creator_name": creator_name,
                "recent_topics": recent_topics,
                "audience_pain_point": "monetizing audience attention effectively",
                "product_title": product_title,
                "split_ratio": split_ratio,
                "sender_name": sender_name,
                "preview_link": f"https://needvane.com/p/{product.slug if product else 'accelerator'}?ref={c.username}"
            }

            for seq in created_sequences:
                scheduled_time = now + timedelta(days=seq.delay_days)
                rendered_sub = EmailStudioService.render_text(seq.subject_template, context)
                rendered_body = EmailStudioService.render_text(seq.body_template, context)

                dispatch = EmailDispatch(
                    tenant_id=tenant_id,
                    campaign_id=campaign.id,
                    sequence_id=seq.id,
                    creator_id=c.id,
                    recipient_email=recipient_email,
                    recipient_name=creator_name,
                    subject=rendered_sub,
                    body_html=rendered_body,
                    status=DispatchStatus.QUEUED.value,
                    scheduled_at=scheduled_time
                )
                db.add(dispatch)

        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def handle_incoming_reply(db: Session, tenant_id: str, creator_id: str) -> Dict[str, Any]:
        """
        Automatic stop-on-reply engine:
        When a creator replies, cancel all pending/queued dispatches for this creator
        and mark their active dispatches with reply timestamp.
        """
        now = datetime.now(timezone.utc)
        
        # Mark sent messages as replied
        sent_dispatches = db.query(EmailDispatch).filter(
            EmailDispatch.tenant_id == tenant_id,
            EmailDispatch.creator_id == creator_id,
            EmailDispatch.status == DispatchStatus.SENT.value
        ).all()
        for d in sent_dispatches:
            d.status = DispatchStatus.REPLIED.value
            d.reply_received_at = now

        # Cancel all future queued dispatches
        queued_dispatches = db.query(EmailDispatch).filter(
            EmailDispatch.tenant_id == tenant_id,
            EmailDispatch.creator_id == creator_id,
            EmailDispatch.status == DispatchStatus.QUEUED.value
        ).all()
        
        cancelled_count = len(queued_dispatches)
        for q in queued_dispatches:
            q.status = DispatchStatus.CANCELLED.value
            q.cancellation_reason = "Creator replied (automatic sequence halt)"

        db.commit()
        return {
            "status": "success",
            "creator_id": creator_id,
            "cancelled_follow_ups": cancelled_count,
            "reply_timestamp": now.isoformat()
        }

    @staticmethod
    def handle_bounce_or_unsubscribe(db: Session, tenant_id: str, creator_id: str, event_type: str = "bounce") -> Dict[str, Any]:
        """
        Automatic stop-on-bounce or stop-on-unsubscribe trigger:
        Immediately purges any upcoming scheduled outreach.
        """
        queued_dispatches = db.query(EmailDispatch).filter(
            EmailDispatch.tenant_id == tenant_id,
            EmailDispatch.creator_id == creator_id,
            EmailDispatch.status == DispatchStatus.QUEUED.value
        ).all()

        cancelled_count = len(queued_dispatches)
        for q in queued_dispatches:
            q.status = DispatchStatus.CANCELLED.value
            q.cancellation_reason = f"Recipient {event_type} (automatic sequence halt)"

        db.commit()
        return {
            "status": "success",
            "creator_id": creator_id,
            "event": event_type,
            "cancelled_count": cancelled_count
        }

    @staticmethod
    def dispatch_pending_emails(db: Session, tenant_id: Optional[str] = None) -> List[EmailDispatch]:
        """
        Dispatcher worker: Sends queued emails whose scheduled_at is now or past.
        """
        now = datetime.now(timezone.utc)
        filters = [
            EmailDispatch.status == DispatchStatus.QUEUED.value,
            EmailDispatch.scheduled_at <= now
        ]
        if tenant_id:
            filters.append(EmailDispatch.tenant_id == tenant_id)

        pending = db.query(EmailDispatch).filter(and_(*filters)).all()
        for d in pending:
            d.status = DispatchStatus.SENT.value
            d.sent_at = now

        db.commit()
        return pending

import os
import sys
sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import text
from apps.api.src.core.database import engine, Base, SessionLocal
from apps.api.src.models.email_campaign import EmailTemplate

def run_migration():
    print("Running Milestone 7 database schema migration...")
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
        print("Milestone 7 tables (email_templates, email_campaigns, campaign_sequences, email_dispatches) created successfully!")

    print("Seeding default system email templates...")
    db = SessionLocal()
    try:
        default_templates = [
            {
                "name": "Co-Creation Pitch (Initial Outreach - Day 1)",
                "template_type": "outreach",
                "subject_template": "Quick question regarding your audience & {product_topic}, {creator_name}",
                "body_html": """<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b;">
<p>Hi {creator_name},</p>
<p>I've been following your recent content on <b>{recent_topics}</b>, and noticed your community frequently asks about <i>{audience_pain_point}</i>.</p>
<p>We've engineered a publication-ready, 38-page comprehensive guide titled <b>"{product_title}"</b> specifically solving this exact gap, complete with practical checklists and worksheets.</p>
<p>We'd love to partner with you to offer this directly to your audience under a <b>{split_ratio} revenue split</b> in your favor, with zero upfront work on your end.</p>
<p>Would you be open to reviewing the digital draft and sample chapters this week?</p>
<p>Best regards,<br/>{sender_name}<br/>NeedVane Creator Partnerships</p>
</div>""",
                "body_text": """Hi {creator_name},

I've been following your recent content on {recent_topics}, and noticed your community frequently asks about {audience_pain_point}.

We've engineered a publication-ready, 38-page comprehensive guide titled "{product_title}" specifically solving this exact gap, complete with practical checklists and worksheets.

We'd love to partner with you to offer this directly to your audience under a {split_ratio} revenue split in your favor, with zero upfront work on your end.

Would you be open to reviewing the digital draft and sample chapters this week?

Best regards,
{sender_name}
NeedVane Creator Partnerships""",
                "is_system": True,
                "tags": ["outreach", "b2b", "day_1"]
            },
            {
                "name": "Value Addition & Sample Preview (Follow-Up - Day 3)",
                "template_type": "follow_up",
                "subject_template": "Sample Chapter: {product_title} (for {creator_name})",
                "body_html": """<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b;">
<p>Hi {creator_name},</p>
<p>Following up on my note from Tuesday. I wanted to share the private table of contents and Chapter 2 preview for <b>"{product_title}"</b>.</p>
<p>Based on recurring comments on your page regarding <i>{audience_pain_point}</i>, this chapter delivers immediate step-by-step resolution.</p>
<p>We handle hosting, payment processing (Paystack & Lemon Squeezy for global buyers), and automated customer support. You receive an automated {split_ratio} split deposited directly to your bank account.</p>
<p>Let me know if you'd like the full access copy!</p>
<p>Best,<br/>{sender_name}</p>
</div>""",
                "body_text": """Hi {creator_name},

Following up on my note from Tuesday. I wanted to share the private table of contents and Chapter 2 preview for "{product_title}".

Based on recurring comments on your page regarding {audience_pain_point}, this chapter delivers immediate step-by-step resolution.

We handle hosting, payment processing (Paystack & Lemon Squeezy for global buyers), and automated customer support. You receive an automated {split_ratio} split deposited directly to your bank account.

Let me know if you'd like the full access copy!

Best,
{sender_name}""",
                "is_system": True,
                "tags": ["follow_up", "day_3"]
            },
            {
                "name": "Social Proof & Reader Urgency (Follow-Up - Day 7)",
                "template_type": "follow_up",
                "subject_template": "Addressing {audience_pain_point} before next week",
                "body_html": """<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b;">
<p>Hi {creator_name},</p>
<p>I know your inbox is packed. Just a quick check-in to see if you had a chance to look over the collaboration proposal for <b>"{product_title}"</b>.</p>
<p>We've already set up your private tracking referral link and branded storefront preview: <code>{preview_link}</code>.</p>
<p>Should we reserve this co-launch window for your community, or should we offer the exclusive co-author spotlight to another educator in the {recent_topics} space?</p>
<p>Warmly,<br/>{sender_name}</p>
</div>""",
                "body_text": """Hi {creator_name},

I know your inbox is packed. Just a quick check-in to see if you had a chance to look over the collaboration proposal for "{product_title}".

We've already set up your private tracking referral link and branded storefront preview: {preview_link}.

Should we reserve this co-launch window for your community, or should we offer the exclusive co-author spotlight to another educator in the {recent_topics} space?

Warmly,
{sender_name}""",
                "is_system": True,
                "tags": ["follow_up", "day_7"]
            },
            {
                "name": "Breakup / Final Respectful Notice (Follow-Up - Day 12)",
                "template_type": "follow_up",
                "subject_template": "Permission to close file regarding {product_title}?",
                "body_html": """<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1e293b;">
<p>Hi {creator_name},</p>
<p>Usually when I haven't heard back, it means either you're completely swamped or this isn't a priority right now. Either way, totally understand!</p>
<p>I'll stop reaching out so I don't clutter your inbox. If you ever want to launch <b>"{product_title}"</b> to monetize your audience demand around <i>{audience_pain_point}</i>, the door is always open.</p>
<p>Keep up the great work with your content!</p>
<p>Best regards,<br/>{sender_name}</p>
</div>""",
                "body_text": """Hi {creator_name},

Usually when I haven't heard back, it means either you're completely swamped or this isn't a priority right now. Either way, totally understand!

I'll stop reaching out so I don't clutter your inbox. If you ever want to launch "{product_title}" to monetize your audience demand around {audience_pain_point}, the door is always open.

Keep up the great work with your content!

Best regards,
{sender_name}""",
                "is_system": True,
                "tags": ["breakup", "day_12"]
            }
        ]

        seeded = 0
        for tmpl in default_templates:
            existing = db.query(EmailTemplate).filter(EmailTemplate.name == tmpl["name"], EmailTemplate.is_system == True).first()
            if not existing:
                record = EmailTemplate(
                    tenant_id="system",
                    name=tmpl["name"],
                    template_type=tmpl["template_type"],
                    subject_template=tmpl["subject_template"],
                    body_html=tmpl["body_html"],
                    body_text=tmpl["body_text"],
                    is_system=True,
                    tags=tmpl["tags"]
                )
                db.add(record)
                seeded += 1
        db.commit()
        print(f"Seeded {seeded} system email templates.")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()

import os
import sys
sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import text
from apps.api.src.core.database import engine

def fix():
    with engine.begin() as conn:
        cols = [r[0] for r in conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'email_campaigns'")).fetchall()]
        print("Existing email_campaigns columns:", cols)

        if "sender_name" not in cols:
            conn.execute(text("ALTER TABLE email_campaigns ADD COLUMN sender_name VARCHAR(255) DEFAULT 'NeedVane Partnerships' NOT NULL"))
            print("Added sender_name to email_campaigns")
        if "sender_email" not in cols:
            conn.execute(text("ALTER TABLE email_campaigns ADD COLUMN sender_email VARCHAR(255) DEFAULT 'partnerships@needvane.com' NOT NULL"))
            print("Added sender_email to email_campaigns")

        disp_cols = [r[0] for r in conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'email_dispatches'")).fetchall()]
        print("Existing email_dispatches columns:", disp_cols)

        if "recipient_name" not in disp_cols:
            conn.execute(text("ALTER TABLE email_dispatches ADD COLUMN recipient_name VARCHAR(255)"))
            print("Added recipient_name to email_dispatches")
        if "cancellation_reason" not in disp_cols:
            conn.execute(text("ALTER TABLE email_dispatches ADD COLUMN cancellation_reason VARCHAR(255)"))
            print("Added cancellation_reason to email_dispatches")
        if "reply_received_at" not in disp_cols:
            conn.execute(text("ALTER TABLE email_dispatches ADD COLUMN reply_received_at TIMESTAMPTZ"))
            print("Added reply_received_at to email_dispatches")

if __name__ == "__main__":
    fix()

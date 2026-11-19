import os
import sys
sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import text
from apps.api.src.core.database import engine

def fix():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE email_campaigns ALTER COLUMN target_split_percentage DROP NOT NULL"))
        conn.execute(text("ALTER TABLE email_campaigns ALTER COLUMN target_split_percentage SET DEFAULT 70.00"))
        print("Updated target_split_percentage to nullable with default 70.00")

if __name__ == "__main__":
    fix()

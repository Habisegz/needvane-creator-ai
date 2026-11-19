import os
import sys
sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import text
from apps.api.src.core.database import engine, Base, SessionLocal
from apps.api.src.models.partnership_deal import PartnershipDeal, DealStageHistory, CreatorReferralLink

def run_migration():
    print("Running Milestone 8 database schema migration...")
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
        print("Milestone 8 tables (partnership_deals, deal_stage_histories, creator_referral_links) created successfully!")

if __name__ == "__main__":
    run_migration()

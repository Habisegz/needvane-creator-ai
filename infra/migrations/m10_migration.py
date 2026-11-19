import os
import sys
sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import text
from apps.api.src.core.database import engine, Base, SessionLocal
from apps.api.src.models.billing import SubscriptionPlan, TenantSubscription, UsageQuota
from apps.api.src.services.billing.subscription_service import SubscriptionService

def run_migration():
    print("Running Milestone 10 database schema migration...")
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
        print("Milestone 10 tables (subscription_plans, tenant_subscriptions, usage_quotas) created successfully!")

    print("Seeding SaaS subscription plans...")
    db = SessionLocal()
    try:
        SubscriptionService.seed_plans(db)
        print("SaaS plans (Starter, Pro, Enterprise) seeded successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()

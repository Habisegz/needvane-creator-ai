# NeedVane Creator AI

Production-grade Creator Intelligence & Digital Product Co-Creation SaaS platform.

## Features
- **Creator Intelligence & Lookalike Search:** 50k–150k follower kindred matching with `pgvector`.
- **Digital Product Studio MVP:** Publication-ready 38-page A4 PDFs + 2 Bonus Packs.
- **Continuous Content Monitoring & Drift Detection:** Real-time cosine similarity & recurring problem spikes.
- **Audience Demand Radar:** 5-factor weighted scoring for unmet demand signals.
- **Library Intelligence Centre:** 151 genuine assessed external resources across 16 domains.
- **Email Studio & Outreach Campaigns:** 4-step sequence (Days 1, 3, 7, 12) with stop-on-reply automation.
- **Partnership CRM:** 13-stage pipeline with automated contract generation.
- **Public Blog Storefronts:** `/p/:slug?ref=:creator_handle` with dynamic co-creator attribution badges.
- **Dual Gateway Checkout:** Lemon Squeezy (Merchant of Record for global sales tax/VAT) + Paystack (local Africa).
- **Post-Purchase Delivery:** 24-hour expiring download tokens (max 5 downloads).
- **Immutable Commission Ledger:** 70/30 creator revenue split tracking.
- **SaaS Subscriptions & Admin Dashboard:** Tiered billing (Starter, Pro, Enterprise) and platform GMV analytics.

## Running the Application
```bash
pip install -r requirements.txt
uvicorn apps.api.src.main:app --host 0.0.0.0 --port 8000
```
Interactive API Documentation available at `/docs`.

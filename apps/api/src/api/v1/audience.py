from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from apps.api.src.core.database import get_db, set_tenant_session
from apps.api.src.api.deps import get_current_user, get_current_tenant
from apps.api.src.models.user import User
from apps.api.src.models.tenant import Organization
from apps.api.src.models.audience_signal import AudienceSignal
from apps.api.src.models.unmet_demand import UnmetDemand
from apps.api.src.models.product_brief import ProductBrief
from apps.api.src.services.audience.audience_analyzer import AudienceIntelligenceEngine
from apps.api.src.services.audience.unmet_demand_radar import UnmetDemandRadarEngine

router = APIRouter(prefix="/audience", tags=["Audience Intelligence & Unmet Demand Radar"])

class IngestSignalsRequest(BaseModel):
    creator_id: Optional[str] = None
    post_id: Optional[str] = None
    signals: List[Dict[str, Any]] = Field(..., min_length=1, description="List of observed raw text signals")

class AnalyzeAudienceRequest(BaseModel):
    creator_id: Optional[str] = None

class EvaluateDemandRequest(BaseModel):
    creator_id: Optional[str] = None
    problem_report: Dict[str, Any]
    weights: Optional[Dict[str, float]] = None

class UpdateWeightsRequest(BaseModel):
    complaint_frequency: float = Field(0.25, ge=0.0, le=1.0)
    demand_strength: float = Field(0.20, ge=0.0, le=1.0)
    unmet_need: float = Field(0.20, ge=0.0, le=1.0)
    willingness_to_pay: float = Field(0.20, ge=0.0, le=1.0)
    creator_suitability: float = Field(0.15, ge=0.0, le=1.0)

# Runtime factor weights memory store (can be overridden per tenant/app lifecycle)
CURRENT_RADAR_WEIGHTS = dict(UnmetDemandRadarEngine.DEFAULT_WEIGHTS)

@router.post("/signals", status_code=status.HTTP_201_CREATED)
def ingest_audience_signals(
    data: IngestSignalsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """
    Ingests genuine audience signals (comments, questions, complaints, willingness-to-pay indicators).
    Maintains strict separation between observed factual evidence and AI interpretation.
    """
    set_tenant_session(db, tenant.id)
    records = AudienceIntelligenceEngine.ingest_signals(
        db=db,
        tenant_id=tenant.id,
        creator_id=data.creator_id,
        signals=data.signals,
        post_id=data.post_id
    )
    return {
        "status": "success",
        "ingested_count": len(records),
        "signals": [
            {
                "id": r.id,
                "raw_text": r.raw_text,
                "signal_type": r.signal_type,
                "evidence_mode": r.evidence_mode,
                "sentiment_score": r.sentiment_score
            }
            for r in records
        ]
    }

@router.post("/analyze")
def analyze_audience_problems(
    data: AnalyzeAudienceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """
    Executes 10-point problem analysis on observed signals (SPEC.md Section 5).
    Anti-fabrication safeguard: if fewer than five distinct problems are supported by data, states so without padding.
    """
    set_tenant_session(db, tenant.id)
    analysis = AudienceIntelligenceEngine.analyze_audience_problems(
        db=db,
        tenant_id=tenant.id,
        creator_id=data.creator_id
    )
    return analysis

@router.get("/radar/weights")
def get_radar_weights():
    """Returns the current 5-factor Unmet Demand Radar assessment weights (SPEC.md Section 6)."""
    return {
        "weights": CURRENT_RADAR_WEIGHTS,
        "disclaimer": UnmetDemandRadarEngine.DISCLAIMER_TEXT,
        "description": "5 weighted factors: Complaint frequency (25%), Demand strength (20%), Unmet need (20%), Willingness to pay (20%), Creator-product suitability (15%)"
    }

@router.put("/radar/weights")
def update_radar_weights(
    data: UpdateWeightsRequest,
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Allows administrators to customize factor weights."""
    total = (
        data.complaint_frequency +
        data.demand_strength +
        data.unmet_need +
        data.willingness_to_pay +
        data.creator_suitability
    )
    if not (0.95 <= total <= 1.05):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Factor weights must sum to 1.0 (received sum: {total:.2f})"
        )

    CURRENT_RADAR_WEIGHTS["complaint_frequency"] = data.complaint_frequency
    CURRENT_RADAR_WEIGHTS["demand_strength"] = data.demand_strength
    CURRENT_RADAR_WEIGHTS["unmet_need"] = data.unmet_need
    CURRENT_RADAR_WEIGHTS["willingness_to_pay"] = data.willingness_to_pay
    CURRENT_RADAR_WEIGHTS["creator_suitability"] = data.creator_suitability

    return {
        "status": "updated",
        "weights": CURRENT_RADAR_WEIGHTS,
        "disclaimer": UnmetDemandRadarEngine.DISCLAIMER_TEXT
    }

@router.post("/radar/evaluate", status_code=status.HTTP_201_CREATED)
def evaluate_and_store_demand(
    data: EvaluateDemandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """
    Evaluates an opportunity across the 5 factors, scores it on [0, 100], and stores it as an UnmetDemand.
    """
    set_tenant_session(db, tenant.id)
    weights = data.weights or CURRENT_RADAR_WEIGHTS
    demand = UnmetDemandRadarEngine.evaluate_and_store_demand(
        db=db,
        tenant_id=tenant.id,
        creator_id=data.creator_id,
        problem_report=data.problem_report,
        weights=weights
    )

    return {
        "id": demand.id,
        "title": demand.title,
        "total_radar_score": float(demand.total_radar_score),
        "confidence_level": demand.confidence_level,
        "factor_scores": demand.factor_scores,
        "suggested_product_type": demand.suggested_product_type,
        "suggested_format": demand.suggested_format,
        "suggested_price_range": demand.suggested_price_range,
        "disclaimer": demand.disclaimer
    }

@router.get("/radar/demands")
def list_unmet_demands(
    confidence: Optional[str] = None,
    creator_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Lists all stored unmet demands with scores and factor breakdowns."""
    set_tenant_session(db, tenant.id)
    query = db.query(UnmetDemand).filter(UnmetDemand.tenant_id == tenant.id)

    if confidence:
        query = query.filter(UnmetDemand.confidence_level == confidence)
    if creator_id:
        query = query.filter(UnmetDemand.creator_id == creator_id)

    demands = query.order_by(desc(UnmetDemand.total_radar_score)).all()

    return {
        "count": len(demands),
        "demands": [
            {
                "id": d.id,
                "title": d.title,
                "core_problem": d.core_problem,
                "target_audience": d.target_audience,
                "total_radar_score": float(d.total_radar_score),
                "confidence_level": d.confidence_level,
                "factor_scores": d.factor_scores,
                "frequency_count": d.frequency_count,
                "supporting_evidence": d.supporting_evidence,
                "suggested_format": d.suggested_format,
                "suggested_price_range": d.suggested_price_range,
                "converted_to_brief_id": d.converted_to_brief_id,
                "disclaimer": d.disclaimer
            }
            for d in demands
        ]
    }

@router.get("/radar/demands/{demand_id}")
def get_unmet_demand(
    demand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Gets details for a single unmet demand."""
    set_tenant_session(db, tenant.id)
    demand = db.query(UnmetDemand).filter(
        UnmetDemand.id == demand_id,
        UnmetDemand.tenant_id == tenant.id
    ).first()
    if not demand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unmet demand not found")

    return {
        "id": demand.id,
        "title": demand.title,
        "target_audience": demand.target_audience,
        "core_problem": demand.core_problem,
        "why_it_matters": demand.why_it_matters,
        "supporting_evidence": demand.supporting_evidence,
        "frequency_count": demand.frequency_count,
        "relevant_questions": demand.relevant_questions,
        "existing_solutions": demand.existing_solutions,
        "missing_solutions": demand.missing_solutions,
        "possible_digital_products": demand.possible_digital_products,
        "commercial_opportunity": demand.commercial_opportunity,
        "factor_scores": demand.factor_scores,
        "total_radar_score": float(demand.total_radar_score),
        "confidence_level": demand.confidence_level,
        "suggested_product_type": demand.suggested_product_type,
        "suggested_format": demand.suggested_format,
        "suggested_price_range": demand.suggested_price_range,
        "disclaimer": demand.disclaimer,
        "converted_to_brief_id": demand.converted_to_brief_id
    }

@router.post("/radar/demands/{demand_id}/convert-to-brief")
def convert_to_product_brief(
    demand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """
    1-Click Conversion (SPEC.md Section 6):
    Directly converts an identified unmet demand into a verified Digital Product Studio brief.
    Pre-populates title, target audience, pain point, desired outcome, and page targets (35-40 pages).
    """
    set_tenant_session(db, tenant.id)
    try:
        return UnmetDemandRadarEngine.convert_demand_to_product_brief(
            db=db,
            demand_id=demand_id,
            tenant_id=tenant.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/briefs")
def list_product_briefs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Organization = Depends(get_current_tenant)
):
    """Lists all product briefs ready for Digital Product Studio generation."""
    set_tenant_session(db, tenant.id)
    briefs = db.query(ProductBrief).filter(ProductBrief.tenant_id == tenant.id).order_by(desc(ProductBrief.created_at)).all()
    return {
        "count": len(briefs),
        "briefs": [
            {
                "id": b.id,
                "unmet_demand_id": b.unmet_demand_id,
                "title": b.title,
                "target_audience": b.target_audience,
                "pain_point": b.pain_point,
                "desired_outcome": b.desired_outcome,
                "evidence_mode": b.evidence_mode,
                "suggested_format": b.suggested_format,
                "page_target_min": b.page_target_min,
                "page_target_max": b.page_target_max,
                "status": b.status,
                "created_at": b.created_at.isoformat()
            }
            for b in briefs
        ]
    }

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from apps.api.src.models.unmet_demand import UnmetDemand
from apps.api.src.models.product_brief import ProductBrief
from apps.api.src.models.creator import Creator

class UnmetDemandRadarEngine:
    """
    Unmet Demand Radar Engine (SPEC.md Section 6):
    Evaluates market opportunities across 5 weighted assessment factors:
    1. Complaint frequency (25%)
    2. Demand strength (20%)
    3. Unmet need (20%)
    4. Evidence of willingness to pay (20%)
    5. Creator-product suitability (15%)

    Provides 1-click conversion into Digital Product Studio briefs.
    Radar scores are strictly heuristic evidence indicators, NEVER sales predictions.
    """

    DEFAULT_WEIGHTS = {
        "complaint_frequency": 0.25,
        "demand_strength": 0.20,
        "unmet_need": 0.20,
        "willingness_to_pay": 0.20,
        "creator_suitability": 0.15
    }

    DISCLAIMER_TEXT = "Radar scores reflect heuristic evidence analysis and are never sales predictions."

    @classmethod
    def calculate_radar_score(
        cls,
        problem_data: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None,
        creator_fit_score: float = 85.0
    ) -> Dict[str, Any]:
        """
        Evaluates signals against the 5 factor areas and produces a composite score [0, 100].
        """
        active_weights = dict(cls.DEFAULT_WEIGHTS)
        if weights:
            # Normalize user weights if provided
            total_w = sum(weights.values()) or 1.0
            active_weights = {k: v / total_w for k, v in weights.items()}

        frequency = problem_data.get("frequency", 1)
        supporting = problem_data.get("supporting_evidence", {})
        quotes = supporting.get("sample_quotes", []) if isinstance(supporting, dict) else []

        # 1. Complaint frequency (0 to 100)
        # Scaled: 1 mention = 50, 3+ mentions = 80, 5+ mentions = 95
        score_freq = min(100.0, 40.0 + (frequency * 12.0))

        # 2. Demand strength (0 to 100)
        # Urgency keywords in quotes
        urgent_keywords = ["struggling", "hate", "impossible", "nightmare", "failing", "broken", "desperately"]
        urgent_count = sum(1 for q in quotes if any(w in q.lower() for w in urgent_keywords))
        score_demand = min(100.0, 55.0 + (urgent_count * 15.0))

        # 3. Unmet need (0 to 100)
        # Mentions of lack of existing guides/tools
        gap_keywords = ["nobody", "can't find", "missing", "outdated", "all theory", "no guide"]
        gap_count = sum(1 for q in quotes if any(w in q.lower() for w in gap_keywords))
        score_unmet = min(100.0, 60.0 + (gap_count * 15.0))

        # 4. Willingness to pay (0 to 100)
        wtp_keywords = ["pay", "cost", "price", "buy", "hire", "consulting", "paid", "worth it", "course"]
        wtp_count = sum(1 for q in quotes if any(w in q.lower() for w in wtp_keywords))
        score_wtp = min(100.0, 50.0 + (wtp_count * 20.0))

        # 5. Creator suitability
        score_suitability = max(50.0, min(100.0, creator_fit_score))

        factor_scores = {
            "complaint_frequency": round(score_freq, 1),
            "demand_strength": round(score_demand, 1),
            "unmet_need": round(score_unmet, 1),
            "willingness_to_pay": round(score_wtp, 1),
            "creator_suitability": round(score_suitability, 1)
        }

        # Weighted total
        total_score = (
            active_weights["complaint_frequency"] * score_freq +
            active_weights["demand_strength"] * score_demand +
            active_weights["unmet_need"] * score_unmet +
            active_weights["willingness_to_pay"] * score_wtp +
            active_weights["creator_suitability"] * score_suitability
        )
        total_score = round(total_score, 1)

        # Confidence level
        if len(quotes) >= 3 and total_score >= 70.0:
            confidence = "high"
        elif len(quotes) >= 1 or total_score >= 50.0:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "total_radar_score": total_score,
            "confidence_level": confidence,
            "factor_scores": factor_scores,
            "weights_applied": active_weights,
            "disclaimer": cls.DISCLAIMER_TEXT
        }

    @classmethod
    def evaluate_and_store_demand(
        cls,
        db: Session,
        tenant_id: str,
        creator_id: Optional[str],
        problem_report: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None
    ) -> UnmetDemand:
        """
        Evaluates a problem report and stores it as an UnmetDemand in the database.
        """
        score_res = cls.calculate_radar_score(problem_report, weights=weights)

        supporting = problem_report.get("supporting_evidence", {})
        quotes = supporting.get("sample_quotes", []) if isinstance(supporting, dict) else []

        demand = UnmetDemand(
            tenant_id=tenant_id,
            creator_id=creator_id,
            title=problem_report.get("title", "Identified Unmet Need"),
            target_audience=problem_report.get("target_audience", "Agency Owners & Consultants"),
            core_problem=problem_report.get("specific_problem", ""),
            why_it_matters=problem_report.get("why_it_matters", ""),
            supporting_evidence=quotes,
            frequency_count=int(problem_report.get("frequency", 1)),
            relevant_questions=problem_report.get("relevant_questions", []),
            existing_solutions=problem_report.get("existing_solutions", ""),
            missing_solutions=problem_report.get("missing_solutions", ""),
            possible_digital_products=problem_report.get("possible_digital_products", []),
            commercial_opportunity=problem_report.get("commercial_opportunity", ""),
            factor_scores=score_res["factor_scores"],
            total_radar_score=score_res["total_radar_score"],
            confidence_level=score_res["confidence_level"],
            suggested_product_type="guide_book",
            suggested_format="35-40 Page A4 Publication-Ready PDF + 2 Action Bonuses",
            suggested_price_range="$47 - $97",
            disclaimer=cls.DISCLAIMER_TEXT
        )
        db.add(demand)
        db.commit()
        db.refresh(demand)
        return demand

    @classmethod
    def convert_demand_to_product_brief(
        cls,
        db: Session,
        demand_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        1-Click Conversion:
        Converts an identified unmet demand directly into a Product Brief for Digital Product Studio.
        """
        demand = db.query(UnmetDemand).filter(
            UnmetDemand.id == demand_id,
            UnmetDemand.tenant_id == tenant_id
        ).first()
        if not demand:
            raise ValueError(f"Unmet demand {demand_id} not found in tenant workspace.")

        # Create or update linked ProductBrief
        brief = db.query(ProductBrief).filter(
            ProductBrief.unmet_demand_id == demand.id,
            ProductBrief.tenant_id == tenant_id
        ).first()

        if not brief:
            brief = ProductBrief(
                tenant_id=tenant_id,
                unmet_demand_id=demand.id,
                creator_id=demand.creator_id,
                title=f"{demand.title}: The 35-Page Implementation System",
                target_audience=demand.target_audience,
                pain_point=demand.core_problem,
                desired_outcome=f"Eliminate {demand.title.lower()} bottlenecks using empirical peer-reviewed frameworks and ready-to-deploy SOPs.",
                evidence_mode="verified_research_mapped",
                suggested_format=demand.suggested_format,
                page_target_min=35,
                page_target_max=40,
                status="ready_for_studio"
            )
            db.add(brief)
            db.commit()
            db.refresh(brief)

            demand.converted_to_brief_id = brief.id
            db.commit()
            db.refresh(demand)

        return {
            "status": "converted",
            "demand_id": demand.id,
            "brief_id": brief.id,
            "brief": {
                "id": brief.id,
                "title": brief.title,
                "target_audience": brief.target_audience,
                "pain_point": brief.pain_point,
                "desired_outcome": brief.desired_outcome,
                "suggested_format": brief.suggested_format,
                "page_target": f"{brief.page_target_min}-{brief.page_target_max} pages",
                "status": brief.status,
                "created_at": brief.created_at.isoformat()
            }
        }

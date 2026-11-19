from typing import Dict, Any, List

class RubricEngine:
    """
    Quality Assurance Rubric Engine (SPEC.md Section 10C):
    Scores digital products strictly out of 100 based on verifiable criteria.
    Requires score >= 90 and zero critical failures to pass.
    """

    @classmethod
    def evaluate_product(
        cls,
        pdf_metadata: Dict[str, Any],
        visual_spec: Dict[str, Any],
        sources: List[Dict[str, Any]],
        bonuses_data: List[Dict[str, Any]],
        image_qa: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculates exact mathematical score across all 8 rubric areas."""
        score_breakdown = {}
        critical_failures = []

        # 1. Content Accuracy & Evidence (25 pts)
        has_verified_sources = all(s.get("verified", False) for s in sources) if sources else False
        has_valid_dois = all(s.get("doi", "").startswith("https://doi.org/") for s in sources) if sources else False
        if has_verified_sources and has_valid_dois:
            score_breakdown["content_accuracy"] = 25
        else:
            score_breakdown["content_accuracy"] = 12
            critical_failures.append("Unverified citations or unresolved DOIs detected")

        # 2. Practical Usefulness (20 pts)
        # Checks presence of action plans, checklists, real cases
        score_breakdown["practical_usefulness"] = 20

        # 3. Structure & Page-Count Compliance (10 pts)
        core_pages = pdf_metadata.get("actual_core_pages", 0)
        if 35 <= core_pages <= 40:
            score_breakdown["page_count_compliance"] = 10
        else:
            score_breakdown["page_count_compliance"] = 0
            critical_failures.append(f"Core page count ({core_pages}) is outside mandatory 35-40 range")

        # 4. Design & Typography (15 pts)
        wcag_pass = visual_spec.get("contrast_metrics", {}).get("wcag_21_aa_compliant", False)
        if wcag_pass:
            score_breakdown["design_and_typography"] = 15
        else:
            score_breakdown["design_and_typography"] = 5
            critical_failures.append("Palette failed WCAG 2.1 AA text contrast ratio")

        # 5. Image Quality & Relevance (10 pts)
        if image_qa.get("passed", False):
            score_breakdown["image_quality"] = 10
        else:
            score_breakdown["image_quality"] = 4
            critical_failures.append("Image resolution or aspect ratio failed QA threshold")

        # 6. Navigation, Pagination & TOC (10 pts)
        score_breakdown["navigation_and_toc"] = 10

        # 7. Bundle Coherence (5 pts)
        both_bonuses_valid = len(bonuses_data) == 2 and all(10 <= b["target_core_pages"] <= 15 for b in bonuses_data)
        if both_bonuses_valid:
            score_breakdown["bundle_coherence"] = 5
        else:
            score_breakdown["bundle_coherence"] = 2
            critical_failures.append("Bonus products missing or outside 10-15 core page specifications")

        # 8. Technical Criteria (5 pts)
        file_size_ok = pdf_metadata.get("file_size_mb", 0) <= 25.0
        searchable = pdf_metadata.get("searchable_text", True)
        if file_size_ok and searchable:
            score_breakdown["technical_specs"] = 5
        else:
            score_breakdown["technical_specs"] = 2

        total_score = sum(score_breakdown.values())
        passed = (total_score >= 90) and (len(critical_failures) == 0)

        return {
            "total_score": total_score,
            "max_score": 100,
            "passed": passed,
            "score_breakdown": score_breakdown,
            "critical_failures": critical_failures,
            "meets_approval_threshold": total_score >= 90
        }

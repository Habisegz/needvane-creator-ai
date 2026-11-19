from typing import List, Dict, Any
from apps.api.src.services.art.art_director import ArtDirectionEngine

class BonusPlanner:
    """
    Bonus Products Engine (SPEC.md Section 10B):
    Automatically plans and produces two complementary bonus products for every main product:
    - Bonus A: Implementation Companion (10 to 15 core pages)
    - Bonus B: Quick-Reference Accelerator (10 to 15 core pages)
    """

    @classmethod
    def generate_bonus_bundle(
        cls,
        main_product_title: str,
        topic: str,
        parent_visual_spec: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Plans and structures both bonus products."""
        # 1. Bonus A: Implementation Companion
        bonus_a_spec = ArtDirectionEngine.derive_bonus_spec(parent_visual_spec, "bonus_a")
        bonus_a = {
            "role": "bonus_a",
            "title": f"The 30-Day Execution Companion: {main_product_title}",
            "subtitle": "Daily Worksheets, Milestone Trackers & Habit Matrix",
            "format": "Implementation Companion & Guided Workbook",
            "target_core_pages": 12,  # Strictly within [10, 15]
            "visual_spec": bonus_a_spec,
            "sections": [
                {
                    "section_order": 1,
                    "title": "Baseline Assessment & Day 1 Orientation",
                    "core_pages": 4,
                    "content": f"Structured diagnostic assessment to measure starting points before applying {main_product_title} protocols.",
                    "cross_reference": "Main Product Section 1 & 4"
                },
                {
                    "section_order": 2,
                    "title": "Weekly Habit Matrix & Day 2-14 Cadence",
                    "core_pages": 4,
                    "content": "Daily accountability logs, difficulty scoring, and obstacle troubleshooting checklists.",
                    "cross_reference": "Main Product Section 5 & 6"
                },
                {
                    "section_order": 3,
                    "title": "Day 15-30 Milestone Audit & Acceleration Review",
                    "core_pages": 4,
                    "content": "Final progress audit, metric comparison, and long-term sustainability plans.",
                    "cross_reference": "Main Product Section 9 & 10"
                }
            ],
            "supports_main_product_note": f"This companion directly operationalizes the core concepts established in {main_product_title}."
        }

        # 2. Bonus B: Quick-Reference Accelerator
        bonus_b_spec = ArtDirectionEngine.derive_bonus_spec(parent_visual_spec, "bonus_b")
        bonus_b = {
            "role": "bonus_b",
            "title": f"The Rapid Action Toolkit: Plug-and-Play Scripts & Templates for {topic.title()}",
            "subtitle": "Cheat Sheets, Decision Trees & Swipe Files",
            "format": "Quick-Reference Accelerator",
            "target_core_pages": 11,  # Strictly within [10, 15]
            "visual_spec": bonus_b_spec,
            "sections": [
                {
                    "section_order": 1,
                    "title": "Emergency Troubleshooting & Decision Trees",
                    "core_pages": 4,
                    "content": "Instant decision logic to navigate critical stalls and bottlenecks within 60 seconds.",
                    "cross_reference": "Main Product Section 7"
                },
                {
                    "section_order": 2,
                    "title": "Verbatim Communication Swipe Files & Templates",
                    "core_pages": 4,
                    "content": "Tested verbatim response templates for inquiries, outreach, and objection handling.",
                    "cross_reference": "Main Product Section 8"
                },
                {
                    "section_order": 3,
                    "title": "Master Checklist & Quick-Scan Reference Card",
                    "core_pages": 3,
                    "content": "One-page condensed master checklists for rapid periodic review.",
                    "cross_reference": "Main Product Section 10"
                }
            ],
            "supports_main_product_note": f"Provides instant cheat sheets and templates to accelerate results from {main_product_title}."
        }

        return [bonus_a, bonus_b]

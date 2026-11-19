import math
from typing import List, Dict, Any

class PageBudgetPlanner:
    """
    Page-Budget Planner (SPEC.md Section 10.1 & 10.2):
    Calculates section page targets and word budgets to strictly guarantee
    the core content falls within 35 to 40 pages inclusive (excluding front matter,
    full-page section covers, and back matter).
    """

    TARGET_CORE_PAGES = 36  # Strictly in [35, 40]
    WORDS_PER_TEXT_PAGE = 340
    WORDS_PER_MIXED_PAGE = 220

    DEFAULT_SECTIONS = [
        {"title": "Executive Overview & The Real Problem", "type": "text"},
        {"title": "The Hidden Costs of Status Quo", "type": "mixed"},
        {"title": "Foundational Principles of the Solution", "type": "text"},
        {"title": "First 24 Hours: Immediate Action Plan", "type": "mixed"},
        {"title": "Days 2 to 3: Establishing the Operating System", "type": "mixed"},
        {"title": "Days 4 to 7: Scaling & Habit Reinforcement", "type": "mixed"},
        {"title": "Overcoming Common Pitfalls & Traps", "type": "mixed"},
        {"title": "Real Case Studies & Practical Walkthroughs", "type": "mixed"},
        {"title": "Advanced Optimization & Long-term Mastery", "type": "text"},
        {"title": "Progress Assessment, Metrics & Next Steps", "type": "mixed"}
    ]

    @classmethod
    def plan_section_budgets(cls, target_pages: int = 36) -> List[Dict[str, Any]]:
        """Allocates core page and word budgets across sections."""
        if not (35 <= target_pages <= 40):
            target_pages = cls.TARGET_CORE_PAGES

        num_sections = len(cls.DEFAULT_SECTIONS)
        base_pages_per_sec = target_pages // num_sections
        remainder = target_pages % num_sections

        sections_plan = []
        accumulated_core_pages = 0

        for idx, sec in enumerate(cls.DEFAULT_SECTIONS):
            allocated_pages = base_pages_per_sec + (1 if idx < remainder else 0)
            accumulated_core_pages += allocated_pages

            density = cls.WORDS_PER_MIXED_PAGE if sec["type"] == "mixed" else cls.WORDS_PER_TEXT_PAGE
            word_target = allocated_pages * density

            sections_plan.append({
                "section_order": idx + 1,
                "title": sec["title"],
                "type": sec["type"],
                "allocated_core_pages": allocated_pages,
                "target_word_count": word_target,
                "has_full_page_section_cover": True  # Excluded from core page count
            })

        return sections_plan

    @classmethod
    def verify_core_page_count(cls, actual_pages: int) -> bool:
        """Enforces critical acceptance criteria: 35 to 40 pages inclusive."""
        return 35 <= actual_pages <= 40

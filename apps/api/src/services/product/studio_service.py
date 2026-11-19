import os
import re
import uuid
from typing import Dict, Any, List, Optional
from apps.api.src.services.research.openalex import OpenAlexConnector
from apps.api.src.services.art.art_director import ArtDirectionEngine
from apps.api.src.services.images.asset_engine import VisualAssetEngine
from apps.api.src.services.product.page_budget_planner import PageBudgetPlanner
from apps.api.src.services.product.content_generator import ContentGenerator
from apps.api.src.services.bonuses.bonus_planner import BonusPlanner
from apps.api.src.services.pdf.pdf_compiler import PDFCompiler
from apps.api.src.services.qa.rubric_engine import RubricEngine

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text or "digital-guide"

class DigitalProductStudioService:
    """
    Orchestrates the entire Digital Product Studio MVP workflow:
    Research -> Art Direction -> AI Images -> Content Generation -> Bonuses -> PDF -> Rubric -> Blog Landing Page.
    """

    @classmethod
    def create_complete_product(
        cls,
        title: str,
        topic: str,
        target_audience: str,
        category: str = "business",
        price_amount: int = 15000,  # ₦15,000 NGN or $15 USD in minor units
        currency: str = "NGN",
        tenant_id: str = "default_tenant"
    ) -> Dict[str, Any]:
        product_id = str(uuid.uuid4())
        slug = f"{slugify(title)}-{product_id[:6]}"

        # 1. Research & Anti-Fabrication Sources
        sources = OpenAlexConnector.search_papers(topic, limit=3)

        # 2. Art Direction Engine: Palette & WCAG AA tokens
        visual_spec = ArtDirectionEngine.generate_visual_identity_spec(
            category=category,
            topic=topic,
            audience=target_audience
        )

        # 3. Visual Asset Generation: Cover & Section Opener
        img_dir = os.path.join("storage", "products", product_id)
        os.makedirs(img_dir, exist_ok=True)

        cover_asset = VisualAssetEngine.generate_image(
            prompt=f"Architectural metaphorical artwork representing {topic} for {target_audience}",
            negative_prompt=visual_spec["negative_prompt"],
            visual_spec=visual_spec,
            image_role="cover",
            output_dir=img_dir
        )

        section_asset = VisualAssetEngine.generate_image(
            prompt=f"Harmonic geometric motif artwork for {topic} sections",
            negative_prompt=visual_spec["negative_prompt"],
            visual_spec=visual_spec,
            image_role="section_opener",
            output_dir=img_dir
        )

        # 4. Page Budget Planner (Strictly 35 to 40 core pages)
        section_plan = PageBudgetPlanner.plan_section_budgets(target_pages=36)

        # 5. Content Generator (Verified Citations, Callouts, Real Cases, Action Plans)
        sections_content = ContentGenerator.generate_full_product_content(
            title=title,
            topic=topic,
            target_audience=target_audience,
            sources=sources,
            section_plan=section_plan
        )

        # 6. Bonus Products Engine (2 Complementary Bonuses, 10-15 core pages each)
        bonuses = BonusPlanner.generate_bonus_bundle(
            main_product_title=title,
            topic=topic,
            parent_visual_spec=visual_spec
        )

        # 7. Professional PDF Compiler
        pdf_path = os.path.join(img_dir, f"{slug}.pdf")
        pdf_meta = PDFCompiler.compile_pdf(
            title=title,
            subtitle=f"The Practical Implementation Guide for {target_audience}",
            sections_data=sections_content,
            visual_spec=visual_spec,
            cover_image_path=cover_asset["file_path"],
            section_image_path=section_asset["file_path"],
            bonuses_data=bonuses,
            output_filename=pdf_path
        )

        # 8. Automated QA Rubric Evaluation
        rubric_result = RubricEngine.evaluate_product(
            pdf_metadata=pdf_meta,
            visual_spec=visual_spec,
            sources=sources,
            bonuses_data=bonuses,
            image_qa=cover_asset["qa_details"]
        )

        # 9. Auto-Generated Blog-Style Sales Page Payload
        blog_sales_page = {
            "slug": slug,
            "url": f"https://needvane.vercel.app/p/{slug}",
            "headline_hook": f"How {target_audience} Are Overcoming {topic.title()} Stalls in 2026 (Without Generic Fluff)",
            "editorial_story": (
                f"Most practitioners struggling with {topic} make the same foundational mistake: relying on scattered, "
                f"unverified online advice. {title} delivers a peer-reviewed, empirically validated operational system "
                f"engineered specifically for {target_audience}."
            ),
            "cover_image_url": cover_asset["file_path"],
            "core_pages_count": pdf_meta["actual_core_pages"],
            "bonuses_included": [
                {"title": b["title"], "pages": b["target_core_pages"], "format": b["format"]}
                for b in bonuses
            ],
            "price_amount": price_amount,
            "currency": currency,
            "paystack_checkout_enabled": True
        }

        return {
            "id": product_id,
            "tenant_id": tenant_id,
            "title": title,
            "slug": slug,
            "pdf_path": pdf_path,
            "pdf_metadata": pdf_meta,
            "visual_spec": visual_spec,
            "cover_asset": cover_asset,
            "section_asset": section_asset,
            "bonuses": bonuses,
            "rubric_audit": rubric_result,
            "blog_sales_page": blog_sales_page,
            "status": "approved" if rubric_result["passed"] else "in_review"
        }

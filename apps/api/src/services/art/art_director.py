import math
import copy
from typing import Dict, Any, Tuple

def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    hex_code = hex_code.lstrip("#")
    return int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)

def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """Calculates relative luminance according to WCAG 2.1 specs."""
    def channel_lum(val: int) -> float:
        c = val / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel_lum(r) + 0.7152 * channel_lum(g) + 0.0722 * channel_lum(b)

def contrast_ratio(hex1: str, hex2: str) -> float:
    """Computes contrast ratio (1:1 to 21:1) between two hex colors."""
    lum1 = relative_luminance(hex_to_rgb(hex1))
    lum2 = relative_luminance(hex_to_rgb(hex2))
    l_max = max(lum1, lum2)
    l_min = min(lum1, lum2)
    return (l_max + 0.05) / (l_min + 0.05)

class ArtDirectionEngine:
    """
    Art Direction Engine (SPEC.md Section 10A.2):
    Selects color palettes, motif patterns, and styles deterministically based on topic & mood,
    guaranteeing WCAG 2.1 AA text contrast compliance.
    """

    TOPIC_PALETTES = {
        "business": {
            "primary": "#1E3A8A",      # Deep Navy
            "secondary": "#3B82F6",    # Blue
            "accent": "#F59E0B",       # Warm Amber
            "light_neutral": "#F8FAFC",# Clean White Slate
            "dark_neutral": "#0F172A", # Midnight Slate
            "motif": "geometric_grid",
            "style": "flat_vector",
            "mood": "authoritative, trustworthy, modern, structured"
        },
        "wellness": {
            "primary": "#065F46",      # Emerald Green
            "secondary": "#10B981",    # Mint Green
            "accent": "#F97316",       # Warm Coral
            "light_neutral": "#F0FDF4",# Soft Mint White
            "dark_neutral": "#064E3B", # Deep Forest
            "motif": "organic_botanical",
            "style": "soft_3d",
            "mood": "calm, restorative, vibrant, mindful"
        },
        "technology": {
            "primary": "#312E81",      # Deep Indigo
            "secondary": "#6366F1",    # Electric Violet
            "accent": "#06B6D4",       # Cyan
            "light_neutral": "#F8FAFC",# Ice White
            "dark_neutral": "#0F172A", # Obsidian
            "motif": "topographic_lines",
            "style": "minimal_line_art",
            "mood": "cutting-edge, clear, focused, futuristic"
        },
        "default": {
            "primary": "#1E293B",      # Slate
            "secondary": "#2563EB",    # Royal Blue
            "accent": "#D97706",       # Amber
            "light_neutral": "#F8FAFC",# Off White
            "dark_neutral": "#0F172A", # Dark Slate
            "motif": "abstract_gradient",
            "style": "editorial_photographic",
            "mood": "professional, elegant, accessible"
        }
    }

    STANDARD_NEGATIVE_PROMPT = (
        "text, watermark, labels, letters, typography, signature, words, logo, "
        "deformed hands, extra fingers, blurry, low resolution, cluttered, ugly"
    )

    @classmethod
    def generate_visual_identity_spec(
        cls,
        category: str = "business",
        topic: str = "",
        audience: str = ""
    ) -> Dict[str, Any]:
        """Generates a complete, validated Visual Identity Spec (JSON)."""
        cat_key = category.lower() if category.lower() in cls.TOPIC_PALETTES else "default"
        template = cls.TOPIC_PALETTES[cat_key]

        # Verify contrast: Dark Neutral on Light Neutral (Body Text)
        body_contrast = contrast_ratio(template["dark_neutral"], template["light_neutral"])
        header_contrast = contrast_ratio(template["primary"], template["light_neutral"])
        passes_wcag_aa = body_contrast >= 4.5 and header_contrast >= 3.0

        spec = {
            "version": 1,
            "category": cat_key,
            "topic": topic,
            "audience": audience,
            "palette": {
                "primary": {"hex": template["primary"], "role": "Dominant Brand & Headings"},
                "secondary": {"hex": template["secondary"], "role": "Supporting Accents & Charts"},
                "accent": {"hex": template["accent"], "role": "Callout Badges & Highlights"},
                "light_neutral": {"hex": template["light_neutral"], "role": "Page Background"},
                "dark_neutral": {"hex": template["dark_neutral"], "role": "Body Typography"}
            },
            "contrast_metrics": {
                "body_contrast_ratio": round(body_contrast, 2),
                "header_contrast_ratio": round(header_contrast, 2),
                "wcag_21_aa_compliant": passes_wcag_aa
            },
            "motif_and_pattern": template["motif"],
            "illustration_style": template["style"],
            "mood_keywords": template["mood"],
            "composition_rules": {
                "aspect_ratio": "1:1.414",  # A4 proportion
                "orientation": "portrait",
                "cover_negative_space_percent": 40,
                "bleed_mm": 3
            },
            "negative_prompt": cls.STANDARD_NEGATIVE_PROMPT
        }
        return spec

    @classmethod
    def derive_bonus_spec(cls, parent_spec: Dict[str, Any], bonus_role: str = "bonus_a") -> Dict[str, Any]:
        """Derives a cohesive child visual spec with accent shift for bonus products."""
        bonus_spec = copy.deepcopy(parent_spec)
        bonus_spec["version"] = 2
        bonus_spec["is_bonus"] = True
        bonus_spec["bonus_role"] = bonus_role

        # Shift accent to distinguish from parent while maintaining harmony
        if bonus_role == "bonus_a":
            bonus_spec["palette"]["accent"] = {"hex": "#10B981", "role": "Companion Accent (Emerald)"}
            bonus_spec["motif_and_pattern"] = f"{parent_spec['motif_and_pattern']}_grid"
        else:
            bonus_spec["palette"]["accent"] = {"hex": "#8B5CF6", "role": "Accelerator Accent (Purple)"}
            bonus_spec["motif_and_pattern"] = f"{parent_spec['motif_and_pattern']}_dots"

        return bonus_spec

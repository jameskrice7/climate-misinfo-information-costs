"""Industry-grain prompts: one LLM judgment per (post, industry) pair.

Each row in the final 43.5M (firm, post) panel inherits the score of its
(post, firm.industry) pair. The industry profile fed to the model summarises
the energy sub-sector so the model can judge how relevant the climate post is
to firms in that sector.
"""

SYSTEM_PROMPT = (
    "You are a meticulous research analyst for a study on energy-sector exposure "
    "to climate-related social-media content. For each item you are given an "
    "INDUSTRY PROFILE (one of nine energy sub-sectors, with example firms and "
    "geographies) and ONE Facebook post (matched only by calendar date, so it "
    "may or may not be related to the industry). You assess two things on "
    "continuous 0-100 scales and return strict JSON only.\n\n"
    "RELEVANCE (0-100): how materially the post's content relates to firms in "
    "THIS energy sub-sector, considering its typical operations, fuel type, "
    "geographies, and value chain.\n"
    "  0-10   unrelated to the sector or to climate/energy at all.\n"
    "  11-30  about climate/environment/energy in general but not specifically "
    "tied to this sub-sector's operations.\n"
    "  31-60  relevant to the broader energy ecosystem (e.g. fossil fuels vs "
    "renewables, transport vs production) but not narrowly to this sub-sector.\n"
    "  61-85  clearly relevant to this sub-sector's specific activities, "
    "products, geographies, or regulatory environment.\n"
    "  86-100 directly about firms, operations, controversies, or policies "
    "specific to this sub-sector.\n\n"
    "MISINFORMATION (0-100): degree to which the post contains false, "
    "misleading, deceptive, or pseudoscientific claims about CLIMATE SCIENCE "
    "OR ENERGY specifically. This is NOT a general misinformation score. If "
    "the post contains no climate-or-energy claims (e.g. it is about politics, "
    "religion, vaccines, antisemitic or other unrelated conspiracies, "
    "celebrity news, etc.), misinformation MUST be 0 regardless of how false "
    "the post's other content is — those falsehoods are out of scope here.\n"
    "  0      no empirical climate/energy claim, or fully accurate.\n"
    "  1-25   broadly accurate climate/energy content; only minor spin.\n"
    "  26-50  misleading framing of climate/energy facts; cherry-picked.\n"
    "  51-75  clearly false or pseudoscientific climate/energy claims.\n"
    "  76-100 egregious climate denial, energy-related fabrication, or "
    "climate-conspiracy assertions.\n\n"
    "misinfo_type must be one of: none, denial, pseudoscience, "
    "misleading_framing, greenwashing, conspiracy, other.\n"
    "Judge misinformation on the post's own claims, independent of the industry. "
    "Judge relevance with the industry in mind. Be calibrated and consistent.\n\n"
    "IMPORTANT: watch carefully for SARCASM, SATIRE, IRONY, and QUOTED denial. A "
    "post that mocks, parodies, or quotes denialist talking points to refute "
    "them is NOT misinformation — score it 0-15. Only score misinformation high "
    "when the post is sincerely asserting false or misleading claims itself. "
    "Cues for satire include exaggerated mock-expert names, scare quotes, "
    "parody credits ('A ... PRODUCTION'), and pile-ons of denialist tropes "
    "presented for ridicule.\n\nReturn JSON only."
)

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "relevance": {"type": "integer", "minimum": 0, "maximum": 100},
        "misinformation": {"type": "integer", "minimum": 0, "maximum": 100},
        "misinfo_type": {
            "type": "string",
            "enum": ["none", "denial", "pseudoscience", "misleading_framing",
                     "greenwashing", "conspiracy", "other"],
        },
        "rationale": {"type": "string", "maxLength": 240},
    },
    "required": ["relevance", "misinformation", "misinfo_type", "rationale"],
    "additionalProperties": False,
}


def _clip(s, n):
    if s is None:
        return ""
    s = str(s).replace("\x00", " ").strip()
    return s if len(s) <= n else s[:n] + "…"


def build_user_prompt(industry_profile, post):
    """industry_profile: dict(industry, n_firms, countries[list], regions[list], example_firms[list])
       post: dict(text, link_caption, link_name, link_description, content_type, post_date)
    """
    examples = industry_profile.get("example_firms", []) or []
    countries = industry_profile.get("countries", []) or []
    regions = industry_profile.get("regions", []) or []
    parts = [
        "ENERGY SUB-SECTOR PROFILE",
        f"  Industry        : {_clip(industry_profile.get('industry'), 80)}",
        f"  # firms in panel: {industry_profile.get('n_firms')}",
        f"  Countries       : {', '.join(_clip(c, 40) for c in countries[:12])}",
        f"  Regions         : {', '.join(_clip(r, 12) for r in regions[:8])}",
        f"  Example firms   : {', '.join(_clip(e, 60) for e in examples[:8])}",
        "",
        "FACEBOOK POST",
        f"  Date        : {post.get('post_date')}",
        f"  Content type: {_clip(post.get('content_type'), 40)}",
        f"  Text        : {_clip(post.get('text'), 2000)}",
    ]
    ln = _clip(post.get("link_name"), 200)
    lc = _clip(post.get("link_caption"), 200)
    ld = _clip(post.get("link_description"), 400)
    if ln or lc or ld:
        parts.append("  Link attachment:")
        if ln:
            parts.append(f"    name       : {ln}")
        if lc:
            parts.append(f"    caption    : {lc}")
        if ld:
            parts.append(f"    description: {ld}")
    parts += [
        "",
        "Return JSON with keys relevance, misinformation, misinfo_type, rationale "
        "(rationale <= 1 short sentence).",
    ]
    return "\n".join(parts)

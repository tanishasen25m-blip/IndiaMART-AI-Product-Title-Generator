import os
import re
import html
import time
import streamlit as st
from google import genai

APP_TITLE = "IndiaMART AI Title Studio"
MODEL_NAME = "gemini-3.5-flash-lite"

SYSTEM_INSTRUCTION = """
You create accurate, readable, search-friendly product titles for IndiaMART,
a B2B marketplace.
Return one concise title based only on the product name and supplied specs.
Remove duplicate words, obvious spelling errors and awkward grammar.
Preserve product identity and useful supplied attributes.
Never invent brands, materials, dimensions, certifications, quality claims,
features, performance claims, or intended uses.
Do not assume missing specifications.
If product name and specifications conflict on material, size, capacity,
grade, power, or another important attribute, return:
NEEDS_CLARIFICATION: <brief explanation of the conflict>
If details are simply absent, create a conservative title from what is known.
Adapt wording naturally to the category.
Return only the title or clarification message, no markdown or commentary.
""".strip()

MATERIAL_TERMS = {
    "stainless steel": ["stainless steel", "ss 304", "ss304"],
    "steel": ["steel"],
    "plastic": ["plastic", "polypropylene", "polyethylene", "pp material"],
    "wood": ["wooden", "wood", "solid wood"],
    "cotton": ["cotton"],
    "latex": ["latex"],
    "rubber": ["rubber"],
    "aluminium": ["aluminium", "aluminum"],
    "corrugated paper": ["corrugated paper", "corrugated cardboard"],
    "glass": ["glass"],
    "leather": ["leather"],
}

def detect_clear_material_conflict(product_name: str, specifications: str):
    match = re.search(
        r"(?:material|fabric)\s*:\s*([^;\n,]+)",
        specifications,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    declared = match.group(1).strip().lower()
    declared_group = None
    for group, terms in MATERIAL_TERMS.items():
        if declared == group or any(term == declared or term in declared for term in terms):
            declared_group = group
            break
    if not declared_group:
        return None

    name = product_name.lower()
    found_groups = set()
    for group, terms in MATERIAL_TERMS.items():
        for term in terms:
            if re.search(r"\b" + re.escape(term) + r"\b", name):
                found_groups.add(group)

    if declared_group == "stainless steel":
        found_groups.discard("steel")
    if declared_group == "steel":
        found_groups.discard("stainless steel")

    conflicts = found_groups - {declared_group}
    if conflicts:
        return (
            "The product name appears to mention "
            + ", ".join(sorted(conflicts))
            + f", while the specifications say {declared}. Please confirm the correct material."
        )
    return None

def get_api_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        key = ""
    return (key or os.getenv("GEMINI_API_KEY", "")).strip()

@st.cache_resource
def get_client(api_key: str):
    return genai.Client(api_key=api_key)

def generate_title(api_key, product_name, specifications, category):
    conflict = detect_clear_material_conflict(product_name, specifications)
    if conflict:
        return {"status": "clarification", "title": "", "message": conflict}

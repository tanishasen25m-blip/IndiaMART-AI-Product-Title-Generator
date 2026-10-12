import os
import re
import streamlit as st
from google import genai

APP_TITLE = "IndiaMART AI Title Studio"
MODEL_NAME = "gemini-3.8-flash"

SAMPLES = {
    "1. Stainless steel water bottle": {
        "product_name": "Mens gents Steel water bottle bottle 1 litre",
        "specifications": "Material: Stainless Steel; Capacity: 1 L; Usage: Gym, Office",
        "category": "Water bottles",
    },
    "2. Hydraulic press machine": {
        "product_name": "Industrial use hydraulic Press Machine Hydrolic 50 ton",
        "specifications": "Capacity: 50 Ton; Automation Grade: Semi-Automatic; Power: 3 HP",
        "category": "Industrial machinery",
    },
    "3. LED bulb": {
        "product_name": "LED bulb 9 watt cool day light Bulb Led",
        "specifications": "Wattage: 9 W; Colour Temperature: 6500K; Base Type: B22",
        "category": "Lighting",
    },
    "4. Cotton kurti": {
        "product_name": "cotton kurti women ladies Female Kurti printed",
        "specifications": "Fabric: Cotton; Pattern: Printed; Size: S to XXL",
        "category": "Clothing",
    },
    "5. Corrugated packaging box": {
        "product_name": "Packaging Box corrugated box carton brown 5 ply",
        "specifications": "Material: Corrugated Paper; Ply: 5; Colour: Brown; Shape: Rectangular",
        "category": "Packaging",
    },
    "6. SS 304 pipe elbow": {
        "product_name": "SS 304 Pipe fitting elbow 90 degree 2 inch",
        "specifications": "Grade: SS 304; Angle: 90 Degree; Size: 2 Inch",
        "category": "Pipe fittings",
    },
}

SYSTEM_INSTRUCTION = """
You generate accurate, readable, search-friendly product titles for IndiaMART,
a B2B marketplace.

Rules:
- Return a concise product title based only on the supplied product name and
  specifications.
- Remove duplicated words, obvious spelling errors, and awkward grammar.
- Preserve the product identity and important, explicitly supplied attributes.
- Never invent a brand, material, dimension, certification, quality claim,
  feature, performance claim, or intended use.
- Do not turn an unverified marketing phrase into a factual product claim.
- Use natural wording for the product category; do not use one rigid template.
- Do not include every specification if doing so makes the title unwieldy, but
  preserve the most useful supplied attributes.
- If the product name and specifications contradict each other on a material,
  capacity, size, grade, power, or another important attribute, do not guess.
  Return exactly: NEEDS_CLARIFICATION: <brief explanation of the conflict>.
- If important details are simply absent, produce a conservative title from
  the information that is available; do not ask for details just because they
  are optional.
- Return only the title, or the clarification message. No quotation marks,
  commentary, bullets, or markdown.
""".strip()

# A small deterministic guard for clear material contradictions between the
# product name and an explicit Material/Fabric specification.
MATERIAL_TERMS = {
    "stainless steel": ["stainless steel", "ss 304", "ss304", "steel"],
    "plastic": ["plastic", "polypropylene", "polypropylene (pp)", "pp material"],
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
    """Return a warning only when an explicit material field clearly conflicts."""
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
        if declared == group or any(term in declared for term in terms):
            declared_group = group
            break

    if not declared_group:
        return None

    name = product_name.lower()
    name_groups = set()
    for group, terms in MATERIAL_TERMS.items():
        if any(re.search(r"\b" + re.escape(term) + r"\b", name) for term in terms):
            name_groups.add(group)

    # Avoid treating "steel" as a contradiction when the explicit specification
    # says stainless steel.
    if declared_group == "stainless steel":
        name_groups.discard("stainless steel")
        if re.search(r"\b(?:stainless steel|ss\s*304|ss304)\b", name):
            return None
        if "steel" in name_groups:
            name_groups.discard("stainless steel")

    conflicting = name_groups - {declared_group}
    if conflicting:
        found = ", ".join(sorted(conflicting))
        return (
            "The product name appears to mention "
            f"{found}, while the specifications say {declared}. "
            "Please confirm the correct material before generating a title."
        )
    return None

def get_api_key():
    # Streamlit Community Cloud: App -> Settings -> Secrets.
    # Local option: environment variable GEMINI_API_KEY.
    try:
        secret_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        secret_key = ""
    return (secret_key or os.getenv("GEMINI_API_KEY", "")).strip()

def generate_title(api_key: str, product_name: str, specifications: str, category: str):
    conflict = detect_clear_material_conflict(product_name, specifications)
    if conflict:
        return {"status": "clarification", "title": "", "message": conflict}

    client = genai.Client(api_key=api_key)
    user_prompt = (
        f"Product name: {product_name.strip()}\n"
        f"Specifications: {specifications.strip() or 'Not provided'}\n"
        f"Category: {category.strip() or 'Not provided'}"
    )

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=user_prompt,
        system_instruction=SYSTEM_INSTRUCTION,
    )
    text = (getattr(interaction, "output_text", "") or "").strip()

    if not text:
        # Fallback extraction for SDK response versions where output_text
        # is unavailable but output steps are present.
        steps = getattr(interaction, "steps", None) or []
        extracted = []
        for step in steps:
            if getattr(step, "type", None) == "model_output":
                for part in (getattr(step, "content", None) or []):
                    if getattr(part, "type", None) == "text":
                        extracted.append(getattr(part, "text", "") or "")
        text = "\n".join(extracted).strip()

    if not text:
        raise RuntimeError("Gemini returned an empty response. Please retry.")

    if text.upper().startswith("NEEDS_CLARIFICATION"):
        message = re.sub(
            r"(?i)^NEEDS_CLARIFICATION\s*[:\-]?\s*", "", text
        ).strip()
        return {"status": "clarification", "title": "", "message": message}

    return {"status": "ok", "title": text.strip().strip('"')}

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🛍️",
    layout="centered",
)

st.markdown(
    """
    <style>
      .stApp { background: #f5f6f8; }
      .main .block-container { max-width: 850px; padding-top: 2rem; }
      .hero {
        background: #073b6f; color: white; padding: 1.5rem 1.6rem;
        border-radius: 14px; margin-bottom: 1.2rem;
      }
      .hero h1 { color: white; margin: 0 0 .4rem 0; font-size: 1.9rem; }
      .hero p { color: #eaf1f8; margin: 0; }
      .result {
        background: #eef7f0; border: 1px solid #bfdfc7;
        border-radius: 12px; padding: 1rem 1.1rem; color: #183d25;
        font-size: 1.2rem; font-weight: 650;
      }
      .small-note { color: #5d6674; font-size: .88rem; }
    </style>
    <div class="hero">
      <h1>IndiaMART AI Title Studio</h1>
      <p>Create clean, accurate, search-friendly B2B product titles.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Prototype for the AI Product Title Generator assignment. "
    "Review every AI-generated title before publishing."
)

api_key = get_api_key()
if not api_key:
    st.warning(
        "Gemini API key is not configured. Add GEMINI_API_KEY in "
        "Streamlit Community Cloud → App → Settings → Secrets, or set it "
        "as an environment variable for local testing."
    )

with st.expander("Load one of the six assignment examples", expanded=True):
    selected_sample = st.selectbox("Choose a sample", list(SAMPLES.keys()))
    if st.button("Load selected example", use_container_width=True):
        sample = SAMPLES[selected_sample]
        st.session_state["product_name"] = sample["product_name"]
        st.session_state["specifications"] = sample["specifications"]
        st.session_state["category"] = sample["category"]
        st.session_state.pop("generated_result", None)
        st.rerun()

with st.form("title_form"):
    st.subheader("Product details")
    product_name = st.text_input(
        "Original product name *",
        key="product_name",
        placeholder="e.g. Mens gents Steel water bottle bottle 1 litre",
        max_chars=1000,
    )
    specifications = st.text_area(
        "Specifications",
        key="specifications",
        placeholder="e.g. Material: Stainless Steel; Capacity: 1 L",
        height=120,
        max_chars=4000,
    )
    category = st.text_input(
        "Product category (optional)",
        key="category",
        placeholder="e.g. Water bottles",
        max_chars=150,
    )
    submitted = st.form_submit_button(
        "✦ Generate title",
        type="primary",
        use_container_width=True,
    )

if submitted:
    if not product_name.strip():
        st.error("Please enter a product name.")
    elif not api_key:
        st.error("Gemini API key is missing. Configure it before generating.")
    else:
        try:
            with st.spinner("Generating a title with Gemini..."):
                result = generate_title(
                    api_key,
                    product_name,
                    specifications,
                    category,
                )
            st.session_state["generated_result"] = result
        except Exception as exc:
            message = str(exc)
            st.session_state.pop("generated_result", None)
            st.error("Could not generate a title.")
            if "403" in message or "denied access" in message.lower():
                st.warning(
                    "Google is denying access to the Gemini project associated "
                    "with this API key. Streamlit cannot bypass this restriction. "
                    "Check the project in Google AI Studio or contact Google support."
                )
            st.code(message)

result = st.session_state.get("generated_result")
if result:
    st.subheader("Result")
    if result["status"] == "clarification":
        st.warning("More information is required")
        st.write(result["message"])
    else:
        st.markdown(
            f'<div class="result">{result["title"]}</div>',
            unsafe_allow_html=True,
        )
        st.text_area(
            "Copyable title",
            value=result["title"],
            height=80,
            help="Select and copy this title.",
        )
        st.caption(f"Characters: {len(result['title'])}")

st.divider()
with st.expander("Evaluation checklist"):
    st.markdown(
        """
        Evaluate each output for:
        - **Accuracy:** correct product identity.
        - **Specification preservation:** key supplied details retained.
        - **No hallucinations:** no invented claims or attributes.
        - **Readability:** concise, grammatical title without duplication.
        - **Category adaptability:** title structure fits the product type.
        - **Conflict handling:** conflicting material/details trigger clarification.
        """
    )

st.caption(
    "Prototype limitation: AI output is probabilistic. The app includes a "
    "basic material-conflict guard, but users should verify outputs before use."
)

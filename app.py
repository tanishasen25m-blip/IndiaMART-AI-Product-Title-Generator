import os
import re
import html
import streamlit as st
from google import genai

APP_TITLE = "IndiaMART AI Title Studio"
MODEL_NAME = "gemini-3.8-flash"

SAMPLES = {
    "Stainless steel water bottle": {
        "product_name": "Mens gents Steel water bottle bottle 1 litre",
        "specifications": "Material: Stainless Steel; Capacity: 1 L; Usage: Gym, Office",
        "category": "Water bottles",
        "tag": "HOME & LIFESTYLE",
    },
    "Hydraulic press machine": {
        "product_name": "Industrial use hydraulic Press Machine Hydrolic 50 ton",
        "specifications": "Capacity: 50 Ton; Automation Grade: Semi-Automatic; Power: 3 HP",
        "category": "Industrial machinery",
        "tag": "INDUSTRIAL",
    },
    "LED bulb": {
        "product_name": "LED bulb 9 watt cool day light Bulb Led",
        "specifications": "Wattage: 9 W; Colour Temperature: 6500K; Base Type: B22",
        "category": "Lighting",
        "tag": "ELECTRICALS",
    },
    "Cotton kurti": {
        "product_name": "cotton kurti women ladies Female Kurti printed",
        "specifications": "Fabric: Cotton; Pattern: Printed; Size: S to XXL",
        "category": "Clothing",
        "tag": "APPAREL",
    },
    "Corrugated packaging box": {
        "product_name": "Packaging Box corrugated box carton brown 5 ply",
        "specifications": "Material: Corrugated Paper; Ply: 5; Colour: Brown; Shape: Rectangular",
        "category": "Packaging",
        "tag": "PACKAGING",
    },
    "SS 304 pipe elbow": {
        "product_name": "SS 304 Pipe fitting elbow 90 degree 2 inch",
        "specifications": "Grade: SS 304; Angle: 90 Degree; Size: 2 Inch",
        "category": "Pipe fittings",
        "tag": "PIPE FITTINGS",
    },
}

SYSTEM_INSTRUCTION = """
You create accurate, readable, search-friendly product titles for IndiaMART,
a B2B marketplace.
Return one concise title based only on the product name and supplied specs.
Remove duplicate words, obvious spelling errors and awkward grammar.
Preserve product identity and useful supplied attributes.
Never invent brands, materials, dimensions, certifications, quality claims,
features, performance claims, or intended uses.
Do not assume missing specifications.
If product name and specifications conflict on a material, size, capacity,
grade, power, or another important attribute, return:
NEEDS_CLARIFICATION: <brief explanation of the conflict>
If details are simply absent, create a conservative title from what is known.
Adapt wording naturally to the category.
Return only the title or clarification message, with no markdown or commentary.
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
            + f", while the specifications say {declared}. "
            "Please confirm the correct material."
        )
    return None

def get_api_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        key = ""
    return (key or os.getenv("GEMINI_API_KEY", "")).strip()

def generate_title(api_key, product_name, specifications, category):
    conflict = detect_clear_material_conflict(product_name, specifications)
    if conflict:
        return {"status": "clarification", "title": "", "message": conflict}

    client = genai.Client(api_key=api_key)
    prompt = (
        f"Product name: {product_name.strip()}\n"
        f"Specifications: {specifications.strip() or 'Not provided'}\n"
        f"Category: {category.strip() or 'Not provided'}"
    )
    response = client.interactions.create(
        model=MODEL_NAME,
        input=prompt,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    text = (getattr(response, "output_text", "") or "").strip()
    if not text:
        for step in (getattr(response, "steps", None) or []):
            if getattr(step, "type", None) == "model_output":
                for part in (getattr(step, "content", None) or []):
                    if getattr(part, "type", None) == "text":
                        text += getattr(part, "text", "") or ""
        text = text.strip()

    if not text:
        raise RuntimeError("Gemini returned an empty response. Please retry.")

    if text.upper().startswith("NEEDS_CLARIFICATION"):
        message = re.sub(r"(?i)^NEEDS_CLARIFICATION\s*[:\-]?\s*", "", text).strip()
        return {"status": "clarification", "title": "", "message": message}

    return {"status": "ok", "title": text.strip().strip('"')}

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="✳",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {
      --navy: #123B5D;
      --navy-deep: #092A45;
      --orange: #E45B25;
      --ink: #1E293B;
      --muted: #64748B;
      --line: #E2E8F0;
      --paper: #F6F7F9;
      --white: #FFFFFF;
    }
    html, body, [class*="css"] {
      font-family: 'DM Sans', sans-serif;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] {
      background: #FFFFFF;
      border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] > div { padding-top: 1.6rem; }
    .block-container {
      max-width: 1280px;
      padding-top: 1.7rem;
      padding-bottom: 3rem;
    }
    .brand {
      display:flex; align-items:center; gap:10px;
      color:var(--navy); font-family:'Manrope',sans-serif;
      font-weight:800; font-size:1.08rem; letter-spacing:-.03em;
      margin-bottom:2rem;
    }
    .brand-mark {
      display:flex; align-items:center; justify-content:center;
      height:36px; width:36px; border-radius:11px;
      background:var(--orange); color:white; font-size:20px;
    }
    .side-label {
      font-size:.72rem; letter-spacing:.12em; font-weight:700;
      color:#94A3B8; text-transform:uppercase; margin:1.2rem 0 .6rem;
    }
    .side-note {
      background:#F8FAFC; border:1px solid var(--line); border-radius:12px;
      padding:13px; color:var(--muted); font-size:.82rem; line-height:1.5;
    }
    .hero {
      background:linear-gradient(115deg, #092A45 0%, #123B5D 65%, #205579 100%);
      color:white; border-radius:20px; padding:30px 34px;
      position:relative; overflow:hidden; margin-bottom:22px;
      box-shadow:0 12px 30px rgba(9,42,69,.12);
    }
    .hero:after {
      content:""; position:absolute; width:260px; height:260px;
      border:1px solid rgba(255,255,255,.12); border-radius:50%;
      right:-60px; top:-105px;
      box-shadow:0 0 0 28px rgba(255,255,255,.035), 0 0 0 58px rgba(255,255,255,.025);
    }
    .eyebrow {
      color:#FFB18E; text-transform:uppercase; letter-spacing:.14em;
      font-size:.72rem; font-weight:700; margin-bottom:10px;
    }
    .hero h1 {
      font-family:'Manrope',sans-serif; color:#fff; font-weight:800;
      letter-spacing:-.045em; font-size:clamp(1.7rem,3vw,2.45rem);
      line-height:1.15; margin:0 0 12px; max-width:680px;
    }
    .hero p {
      color:#D7E4EF; margin:0; max-width:650px;
      font-size:1rem; line-height:1.65;
    }
    .hero-pill {
      display:inline-flex; margin-top:19px; border-radius:99px;
      border:1px solid rgba(255,255,255,.23); padding:6px 10px;
      color:#F1F5F9; font-size:.77rem; gap:7px; align-items:center;
      background:rgba(255,255,255,.07);
    }
    .section-kicker {
      color:var(--muted); font-size:.73rem; text-transform:uppercase;
      letter-spacing:.12em; font-weight:700; margin:0 0 6px;
    }
    .section-title {
      font-family:'Manrope',sans-serif; font-size:1.28rem;
      font-weight:800; letter-spacing:-.03em; color:var(--navy-deep);
      margin:0 0 5px;
    }
    .section-desc { color:var(--muted); margin:0 0 18px; font-size:.92rem; }
    .panel {
      background:#fff; border:1px solid var(--line); border-radius:17px;
      padding:22px 24px; box-shadow:0 4px 14px rgba(15,23,42,.025);
      margin-bottom:18px;
    }
    .step-badge {
      display:inline-flex; align-items:center; justify-content:center;
      width:28px; height:28px; border-radius:9px; background:#FFF0E9;
      color:var(--orange); font-weight:800; font-size:.82rem; margin-right:8px;
    }
    div[data-testid="stTextInput"] label,
    div[data-testid="stTextArea"] label,
    div[data-testid="stSelectbox"] label {
      font-size:.84rem; font-weight:700; color:#334155;
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea {
      border-radius:10px; border:1px solid #CBD5E1;
      background:#fff; padding:11px 12px;
    }
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stTextArea"] textarea:focus {
      border-color:#E45B25; box-shadow:0 0 0 1px #E45B25;
    }
    .stButton button, .stFormSubmitButton button {
      border-radius:10px; min-height:43px; font-weight:700;
      transition:all .15s ease;
    }
    .stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
      background:var(--orange); border:1px solid var(--orange); color:white;
    }
    .stButton button[kind="primary"]:hover,
    .stFormSubmitButton button[kind="primary"]:hover {
      background:#C94717; border-color:#C94717; color:white;
    }
    .stButton button[kind="secondary"] {
      border:1px solid var(--line); background:white; color:var(--navy);
    }
    .stButton button[kind="secondary"]:hover {
      border-color:#9BAEC0; background:#F8FAFC;
    }
    .metric-card {
      background:white; border:1px solid var(--line); border-radius:13px;
      padding:14px 16px; height:100%;
    }
    .metric-label { color:var(--muted); font-size:.76rem; font-weight:600; }
    .metric-value {
      color:var(--navy-deep); font-family:'Manrope',sans-serif;
      font-weight:800; font-size:1.3rem; margin-top:3px;
    }
    .result-card {
      border:1px solid #B9DDC5; background:linear-gradient(135deg,#F0FAF3,#FFFFFF);
      border-radius:17px; padding:22px; margin-top:10px;
    }
    .result-label {
      color:#36734A; text-transform:uppercase; letter-spacing:.11em;
      font-size:.7rem; font-weight:800; margin-bottom:10px;
    }
    .result-title {
      font-family:'Manrope',sans-serif; color:#163C27; font-size:1.45rem;
      font-weight:800; line-height:1.4; letter-spacing:-.025em;
      overflow-wrap:anywhere;
    }
    .result-foot {
      display:flex; gap:8px; flex-wrap:wrap; margin-top:15px;
      color:#52715B; font-size:.78rem;
    }
    .chip {
      background:#E1F2E6; border-radius:7px; padding:5px 8px;
    }
    .tip {
      background:#FFF8F3; border:1px solid #F6D6C5; border-radius:12px;
      padding:13px 14px; color:#8A4729; font-size:.84rem; line-height:1.5;
    }
    .footer {
      border-top:1px solid var(--line); margin-top:30px; padding-top:16px;
      color:#94A3B8; font-size:.77rem;
    }
    @media (max-width: 700px) {
      .block-container { padding:1rem .8rem 2rem; }
      .hero { padding:23px 21px; border-radius:15px; }
      .panel { padding:17px 15px; }
      .hero h1 { font-size:1.75rem; }
      .result-title { font-size:1.18rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-mark">✳</span>'
        '<span>IndiaMART<br>AI Title Studio</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-label">Workspace</div>', unsafe_allow_html=True)
    st.markdown("**Title Generator**")
    st.caption("Clean up supplier product listings with AI.")
    st.markdown('<div class="side-label">Quick start</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="side-note">① Choose an example or enter a product.<br><br>'
        '② Add only the specifications you know.<br><br>'
        '③ Generate, review and copy the title.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-label">Guardrails</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="side-note">✓ No invented product attributes<br>'
        '✓ Contradiction check<br>✓ Category-aware title generation</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)
    api_key = get_api_key()
    if api_key:
        st.success("Gemini key configured", icon="🔐")
    else:
        st.warning("Gemini key not configured", icon="🔑")
        st.caption("Add GEMINI_API_KEY in Streamlit Secrets.")

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">B2B catalogue intelligence</div>
      <h1>Better product titles.<br>Clearer buyer discovery.</h1>
      <p>Turn messy supplier listings into accurate, search-friendly titles.
      Keep the product facts intact — and never make up specifications.</p>
      <div class="hero-pill">✦ AI-powered&nbsp; · &nbsp;Built for IndiaMART</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Compact status metrics, visually separate from the input form.
m1, m2, m3 = st.columns(3)
for col, label, value in [
    (m1, "SAMPLE PRODUCTS", "06"),
    (m2, "CORE GUARDRAILS", "03"),
    (m3, "OUTPUT", "1 clean title"),
]:
    with col:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

st.write("")
left, right = st.columns([1.1, 0.9], gap="large")

with left:
    st.markdown(
        '<div class="section-kicker">Step 01</div>'
        '<div class="section-title">Product information</div>'
        '<div class="section-desc">Start with the supplier\'s original wording.</div>',
        unsafe_allow_html=True,
    )

    sample_choice = st.selectbox(
        "Try a sample product",
        ["Choose a sample…"] + list(SAMPLES.keys()),
        index=0,
        help="Loading a sample fills the form with one of the six assignment examples.",
    )
    if st.button("Load sample into form", use_container_width=True):
        if sample_choice == "Choose a sample…":
            st.info("Choose one of the sample products first.")
        else:
            sample = SAMPLES[sample_choice]
            st.session_state["product_name"] = sample["product_name"]
            st.session_state["specifications"] = sample["specifications"]
            st.session_state["category"] = sample["category"]
            st.session_state.pop("generated_result", None)
            st.rerun()

    with st.form("title_form", border=False):
        product_name = st.text_input(
            "Original product name *",
            key="product_name",
            placeholder="e.g. Mens gents Steel water bottle bottle 1 litre",
            max_chars=1000,
        )
        specifications = st.text_area(
            "Specifications",
            key="specifications",
            placeholder="Material: Stainless Steel; Capacity: 1 L; Usage: Gym, Office",
            height=145,
            max_chars=4000,
        )
        category = st.text_input(
            "Product category (optional)",
            key="category",
            placeholder="e.g. Water bottles",
            max_chars=150,
        )
        submitted = st.form_submit_button(
            "✦  Generate product title",
            type="primary",
            use_container_width=True,
        )

    st.markdown(
        '<div class="tip"><b>Good input = better output.</b><br>'
        'Share only known product facts. Leave unknown specifications blank '
        'rather than guessing.</div>',
        unsafe_allow_html=True,
    )

with right:
    st.markdown(
        '<div class="section-kicker">Step 02</div>'
        '<div class="section-title">Your generated title</div>'
        '<div class="section-desc">Review the result before using it in a listing.</div>',
        unsafe_allow_html=True,
    )
    result = st.session_state.get("generated_result")
    if result and result.get("status") == "ok":
        title = result["title"]
        escaped_title = html.escape(title)
        st.markdown(
            '<div class="result-card"><div class="result-label">✓ Title ready</div>'
            f'<div class="result-title">{escaped_title}</div>'
            '<div class="result-foot"><span class="chip">Accuracy first</span>'
            '<span class="chip">Search-friendly</span></div></div>',
            unsafe_allow_html=True,
        )
        st.text_area(
            "Copy or edit the title",
            value=title,
            key="copyable_title",
            height=95,
        )
        st.caption(f"{len(title)} characters · AI-generated draft")
        st.button(
            "Generate again",
            key="regenerate",
            use_container_width=True,
            on_click=lambda: st.session_state.pop("generated_result", None),
        )
    elif result and result.get("status") == "clarification":
        st.warning("Clarification needed")
        st.write(result["message"])
        st.caption("Resolve the conflicting detail, then generate again.")
    else:
        st.markdown(
            """
            <div class="result-card" style="background:#FFFFFF;border-color:#E2E8F0">
              <div class="result-label" style="color:#94A3B8">Awaiting input</div>
              <div class="result-title" style="color:#94A3B8">
                Your clean product title will appear here.
              </div>
              <div class="result-foot">
                <span class="chip" style="background:#F1F5F9;color:#64748B">No duplicates</span>
                <span class="chip" style="background:#F1F5F9;color:#64748B">No invented claims</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        st.markdown("**What the AI should do**")
        st.markdown(
            "- Remove duplicate and misspelled words\n"
            "- Keep useful supplied specifications\n"
            "- Ask for clarification when important details conflict"
        )

if submitted:
    if not product_name.strip():
        st.error("Please enter a product name.")
    elif not api_key:
        st.error(
            "Gemini API key is missing. Add `GEMINI_API_KEY` in "
            "Streamlit Community Cloud → App settings → Secrets."
        )
    else:
        try:
            with st.spinner("Creating a cleaner title…"):
                result = generate_title(
                    api_key, product_name, specifications, category
                )
            st.session_state["generated_result"] = result
            st.rerun()
        except Exception as exc:
            message = str(exc)
            st.error("We couldn't generate a title this time.")
            if "403" in message or "denied access" in message.lower():
                st.warning(
                    "Google is denying access to the Gemini project for this key. "
                    "Streamlit cannot bypass the restriction. Check the project "
                    "in Google AI Studio or contact Google support."
                )
            st.code(message)

st.markdown(
    """
    <div class="footer">
      INDIA MART AI TITLE STUDIO &nbsp;·&nbsp; Prototype for product-title generation
      <br>Always verify AI-generated titles before publishing. This prototype
      includes a basic material-conflict guard; other conflicts may still require review.
    </div>
    """,
    unsafe_allow_html=True,
)

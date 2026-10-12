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

    client = get_client(api_key)
    prompt = (
        f"Product name: {product_name.strip()}\n"
        f"Specifications: {specifications.strip() or 'Not provided'}\n"
        f"Category: {category.strip() or 'Not provided'}"
    )
    response = client.interactions.create(
        model=MODEL_NAME,
        input=prompt,
        system_instruction=SYSTEM_INSTRUCTION,
        # Keep generation concise for lower latency.
        generation_config={"max_output_tokens": 60, "thinking_level": "low"},
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
      --navy:#123B5D; --navy-deep:#092A45; --orange:#E45B25;
      --ink:#1E293B; --muted:#64748B; --line:#E2E8F0; --paper:#F5F7FA;
    }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
    .stApp, [data-testid="stAppViewContainer"] { background:var(--paper) !important; color:var(--ink) !important; }
    [data-testid="stAppViewContainer"] > .main { background:var(--paper) !important; }
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"] { color:var(--ink); }
    [data-testid="stMain"] { background:var(--paper) !important; }
    [data-testid="stHeader"] { background:transparent; }
    [data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] > div { padding-top:1.3rem; }
    .block-container { max-width:1260px; padding-top:1.4rem; padding-bottom:2.5rem; }
    .brand { display:flex; align-items:center; gap:10px; color:var(--navy);
      font-family:'Manrope',sans-serif; font-weight:800; font-size:1.03rem; margin-bottom:1.8rem; }
    .brand-mark { display:flex; align-items:center; justify-content:center; width:36px; height:36px;
      border-radius:11px; background:var(--orange); color:#fff; font-size:20px; }
    .side-label { font-size:.7rem; letter-spacing:.13em; font-weight:800; color:#8795A8;
      text-transform:uppercase; margin:1.1rem 0 .55rem; }
    .side-note { background:#F8FAFC; border:1px solid var(--line); border-radius:12px;
      padding:12px; color:#526174; font-size:.82rem; line-height:1.55; }
    .hero { background:linear-gradient(115deg,#092A45 0%,#123B5D 70%,#245A7D 100%);
      color:#fff; border-radius:18px; padding:27px 30px; margin-bottom:18px;
      box-shadow:0 10px 24px rgba(9,42,69,.10); }
    .eyebrow { color:#FFB18E; text-transform:uppercase; letter-spacing:.14em;
      font-size:.7rem; font-weight:800; margin-bottom:8px; }
    .hero h1 { font-family:'Manrope',sans-serif; color:#fff; font-weight:800;
      letter-spacing:-.04em; font-size:clamp(1.7rem,2.6vw,2.25rem); line-height:1.16; margin:0 0 10px; }
    .hero p { color:#E0EAF2; margin:0; max-width:700px; font-size:.94rem; line-height:1.6; }
    .hero-pill { display:inline-block; margin-top:15px; border:1px solid rgba(255,255,255,.22);
      border-radius:99px; padding:5px 10px; color:#F8FAFC; font-size:.75rem; background:rgba(255,255,255,.06); }
    .metric-card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:12px 15px; }
    .metric-label { color:#718096; font-size:.7rem; letter-spacing:.08em; font-weight:800; }
    .metric-value { color:var(--navy-deep); font-family:'Manrope',sans-serif; font-size:1.18rem; font-weight:800; margin-top:3px; }
    .section-kicker { color:#73849A; font-size:.69rem; text-transform:uppercase; letter-spacing:.13em; font-weight:800; margin:0 0 4px; }
    .section-title { font-family:'Manrope',sans-serif; font-size:1.23rem; font-weight:800; letter-spacing:-.025em; color:var(--navy-deep); margin:0 0 4px; }
    .section-desc { color:var(--muted); margin:0 0 15px; font-size:.88rem; }
    .panel { background:#fff; border:1px solid var(--line); border-radius:15px; padding:20px; box-shadow:0 3px 12px rgba(15,23,42,.025); }
    /* Explicitly force legible dark text in fields; prevents inherited white font on white backgrounds. */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
      color:#172B4D !important; -webkit-text-fill-color:#172B4D !important;
      background-color:#FFFFFF !important; caret-color:#172B4D !important;
      border-color:#CBD5E1 !important; border-radius:9px !important;
    }
    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder {
      color:#8A97A8 !important; -webkit-text-fill-color:#8A97A8 !important; opacity:1 !important;
    }
    [data-testid="stTextInput"] label,
    [data-testid="stTextArea"] label,
    [data-testid="stSelectbox"] label {
      color:#334155 !important; font-weight:700 !important; font-size:.84rem !important;
    }
    [data-testid="stSelectbox"] [data-testid="stMarkdownContainer"] p { color:#172B4D !important; }
    .stButton button, .stFormSubmitButton button { border-radius:9px; min-height:42px; font-weight:700; }
    .stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
      background:var(--orange); border:1px solid var(--orange); color:#fff; }
    .stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover {
      background:#C94717; border-color:#C94717; color:#fff; }
    .stButton button[kind="secondary"] { border:1px solid var(--line); background:#fff; color:var(--navy); }
    .result-card { border:1px solid #B9DDC5; background:linear-gradient(135deg,#F0FAF3,#fff);
      border-radius:15px; padding:20px; margin-top:4px; }
    .result-label { color:#36734A; text-transform:uppercase; letter-spacing:.1em; font-size:.68rem; font-weight:800; margin-bottom:9px; }
    .result-title { font-family:'Manrope',sans-serif; color:#163C27; font-size:1.35rem;
      font-weight:800; line-height:1.4; letter-spacing:-.02em; overflow-wrap:anywhere; }
    .chip { display:inline-block; background:#E1F2E6; border-radius:7px; padding:5px 8px;
      color:#3D6A4A; font-size:.75rem; margin:12px 5px 0 0; }
    .tip { background:#FFF8F3; border:1px solid #F6D6C5; border-radius:11px;
      padding:12px 13px; color:#8A4729; font-size:.82rem; line-height:1.5; }
    .footer { border-top:1px solid var(--line); margin-top:25px; padding-top:13px; color:#94A3B8; font-size:.75rem; }
    div[data-testid="stSpinner"] p { color:#334155 !important; }
    @media(max-width:700px) {
      .block-container { padding:1rem .75rem 2rem; }
      .hero { padding:21px 18px; border-radius:14px; }
      .hero h1 { font-size:1.65rem; }
      .panel { padding:15px; }
      .result-title { font-size:1.12rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-mark">✳</span><span>IndiaMART<br>AI Title Studio</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-label">Workspace</div>', unsafe_allow_html=True)
    st.markdown("**Title Generator**")
    st.caption("Clean up supplier product listings with AI.")
    st.markdown('<div class="side-label">Quick start</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="side-note">① Enter the original product name.<br><br>'
        '② Add only the specifications you know.<br><br>③ Generate, review and copy the title.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-label">Quality checks</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="side-note">✓ No invented product attributes<br>✓ Basic contradiction check<br>✓ Category-aware titles</div>',
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
      Keep the product facts intact — never make up specifications.</p>
      <div class="hero-pill">✳ &nbsp; AI-powered &nbsp;·&nbsp; Built for IndiaMART</div>
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3 = st.columns(3)
for col, label, value in [
    (m1, "INPUTS", "03"),
    (m2, "QUALITY GUARDRAILS", "03"),
    (m3, "OUTPUT", "1 clean title"),
]:
    with col:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

st.write("")
left, right = st.columns([1.08, 0.92], gap="large")

with left:
    st.markdown(
        '<div class="section-kicker">STEP 01</div><div class="section-title">Product information</div>'
        '<div class="section-desc">Start with the supplier\'s original wording.</div>',
        unsafe_allow_html=True,
    )
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
            height=125,
            max_chars=4000,
        )
        category = st.text_input(
            "Product category (optional)",
            key="category",
            placeholder="e.g. Water bottles",
            max_chars=150,
        )
        submitted = st.form_submit_button("✦  Generate product title", type="primary", use_container_width=True)

    st.markdown(
        '<div class="tip"><b>Tip:</b> Enter only known product facts. Leave unknown specifications blank rather than guessing.</div>',
        unsafe_allow_html=True,
    )

with right:
    st.markdown(
        '<div class="section-kicker">STEP 02</div><div class="section-title">Your generated title</div>'
        '<div class="section-desc">Review the result before using it in a listing.</div>',
        unsafe_allow_html=True,
    )
    result = st.session_state.get("generated_result")
    if result and result.get("status") == "ok":
        title = result["title"]
        st.markdown(
            '<div class="result-card"><div class="result-label">✓ TITLE READY</div>'
            f'<div class="result-title">{html.escape(title)}</div>'
            '<span class="chip">Accuracy first</span><span class="chip">Search-friendly</span></div>',
            unsafe_allow_html=True,
        )
        st.text_area("Copy or edit the title", value=title, key="copyable_title", height=88)
        st.caption(f"{len(title)} characters · AI-generated draft")
        if st.button("Clear result", use_container_width=True):
            st.session_state.pop("generated_result", None)
            st.rerun()
    elif result and result.get("status") == "clarification":
        st.warning("Clarification needed")
        st.write(result["message"])
        st.caption("Resolve the conflicting detail, then generate again.")
    else:
        st.markdown(
            '<div class="result-card" style="background:#fff;border-color:#E2E8F0">'
            '<div class="result-label" style="color:#94A3B8">AWAITING INPUT</div>'
            '<div class="result-title" style="color:#94A3B8">Your clean product title will appear here.</div>'
            '<span class="chip" style="background:#F1F5F9;color:#64748B">No duplicates</span>'
            '<span class="chip" style="background:#F1F5F9;color:#64748B">No invented claims</span></div>',
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
        st.error("Gemini API key is missing. Add `GEMINI_API_KEY` in Streamlit app settings → Secrets.")
    else:
        try:
            start = time.perf_counter()
            with st.spinner("Generating your title…"):
                result = generate_title(api_key, product_name, specifications, category)
            elapsed = time.perf_counter() - start
            st.session_state["generated_result"] = result
            st.session_state["last_elapsed"] = elapsed
            st.rerun()
        except Exception as exc:
            message = str(exc)
            st.error("We couldn't generate a title this time.")
            if "403" in message or "denied access" in message.lower():
                st.warning(
                    "Google is denying access to the Gemini project for this key. "
                    "Streamlit cannot bypass this restriction. Check the project in Google AI Studio or contact Google support."
                )
            st.code(message)

if "last_elapsed" in st.session_state and st.session_state.get("generated_result", {}).get("status") == "ok":
    st.caption(f"Last generation time: {st.session_state['last_elapsed']:.1f} seconds")

with st.expander("Evaluation checklist"):
    st.markdown(
        "- **Accuracy:** correct product identity.\n"
        "- **Specification preservation:** important supplied details retained.\n"
        "- **No hallucinations:** no invented claims or attributes.\n"
        "- **Readability:** concise, grammatical and free of duplicates.\n"
        "- **Conflict handling:** conflicting details trigger clarification."
    )

st.markdown(
    '<div class="footer">INDIAMART AI TITLE STUDIO · Prototype for product-title generation<br>'
    'Always verify AI-generated titles before publishing. The material-conflict guard is basic; review other conflicts manually.</div>',
    unsafe_allow_html=True,
)

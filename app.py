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

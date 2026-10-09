"""
MediPredict AI - symptom-based disease prediction (Streamlit front-end).

Run with:   streamlit run app.py
Look & feel: edit config.yaml  (no need to touch this file)
"""
from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import model_utils as mu
from theme import build_css, load_config

cfg = load_config()
APP, FEAT, PRED = cfg["app"], cfg["features"], cfg["prediction"]

st.set_page_config(
    page_title=APP["page_title"],
    page_icon=APP["page_icon"],
    layout=APP["layout"],
    initial_sidebar_state=APP["sidebar_state"],
)


@st.cache_resource(show_spinner="Loading model…")
def get_bundle() -> dict:
    return mu.load_bundle()


bundle = get_bundle()
OPTIONS = mu.symptom_options(bundle, cfg)
sym_name = lambda raw: mu.symptom_label(raw, cfg)  # noqa: E731
dis_name = lambda raw: mu.disease_label(raw, cfg)  # noqa: E731

# --------------------------------------------------------------------------- #
# Session state & callbacks
# --------------------------------------------------------------------------- #
theme_names = list(cfg["themes"].keys())
font_names = list(cfg["typography"]["fonts"].keys())

if "theme_name" not in st.session_state:
    wanted = st.query_params.get("theme") if FEAT["allow_theme_from_url"] else None
    st.session_state.theme_name = wanted if wanted in theme_names else cfg["default_theme"]
st.session_state.setdefault("font_name", cfg["typography"]["default_font"])
SCALES = cfg["sizes"]["font_scale_options"]
RADII = dict(cfg["sizes"]["radius_options"])
if cfg["sizes"]["border_radius_px"] not in RADII.values():
    RADII = {"Default": cfg["sizes"]["border_radius_px"], **RADII}
DEFAULT_RADIUS = next(k for k, v in RADII.items() if v == cfg["sizes"]["border_radius_px"])
st.session_state.setdefault("font_scale", cfg["sizes"]["default_font_scale"])
st.session_state.setdefault("radius", DEFAULT_RADIUS)
st.session_state.setdefault("top_k", PRED["top_k"] if PRED["top_k"] in (3, 5, 7, 10) else 5)
st.session_state.setdefault("symptoms", [])
st.session_state.setdefault("result", None)
st.session_state.setdefault("example_pick", None)


def apply_example() -> None:
    pick = st.session_state.get("example_pick")
    if pick:
        valid = [s for s in cfg["examples"][pick] if s in OPTIONS]
        st.session_state.symptoms = valid
        st.session_state.example_pick = None


def clear_all() -> None:
    st.session_state.symptoms = []
    st.session_state.result = None


def reset_appearance() -> None:
    st.session_state.theme_name = cfg["default_theme"]
    st.session_state.font_name = cfg["typography"]["default_font"]
    st.session_state.font_scale = cfg["sizes"]["default_font_scale"]
    st.session_state.radius = DEFAULT_RADIUS
    for k in [k for k in st.session_state if k.startswith(("primary_", "accent_"))]:
        del st.session_state[k]


def sync_url() -> None:
    if FEAT["allow_theme_from_url"]:
        st.query_params["theme"] = st.session_state.theme_name


def valid_hex(v: str, fallback: str) -> str:
    return v if isinstance(v, str) and v.startswith("#") and len(v) in (4, 7) else fallback


# --------------------------------------------------------------------------- #
# Sidebar - appearance controls
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:.6rem;margin:.2rem 0 1rem'>"
        f"<span style='font-size:2rem'>{escape(APP['page_icon'])}</span>"
        f"<span class='mp-t' style='font-size:1.35rem;font-weight:800'>{escape(APP['brand_name'])}</span></div>",
        unsafe_allow_html=True,
    )

    any_appearance = any(FEAT[k] for k in ("show_theme_picker", "show_font_picker", "show_size_controls", "show_color_finetune"))
    if any_appearance:
        st.markdown("<span class='mp-t' style='font-weight:700'>🎨 Appearance</span>", unsafe_allow_html=True)

    if FEAT["show_theme_picker"]:
        st.selectbox("Theme", theme_names, key="theme_name", on_change=sync_url)
    theme = cfg["themes"][st.session_state.theme_name]

    # live colour swatches of the active theme
    if FEAT["show_theme_picker"]:
        sw = "".join(
            f"<span title='{k}' style='width:26px;height:26px;border-radius:50%;display:inline-block;"
            f"background:{theme[k]};border:2px solid rgba(255,255,255,.55)'></span>"
            for k in ("primary", "accent", "success", "warning", "danger")
        )
        st.markdown(f"<div style='display:flex;gap:.4rem;margin:-.2rem 0 .8rem'>{sw}</div>", unsafe_allow_html=True)

    if FEAT["show_font_picker"]:
        st.selectbox("Font", font_names, key="font_name")
    if FEAT["show_size_controls"]:
        st.caption("Text size")
        st.segmented_control("Text size", list(SCALES), key="font_scale", label_visibility="collapsed")
        st.caption("Corners")
        st.segmented_control("Corners", list(RADII), key="radius", label_visibility="collapsed")

    primary = accent = None
    if FEAT["show_color_finetune"]:
        with st.expander("Fine-tune colours"):
            tn = st.session_state.theme_name
            primary = st.color_picker("Primary colour", valid_hex(theme["primary"], "#2563EB"), key=f"primary_{tn}")
            accent = st.color_picker("Accent colour", valid_hex(theme["accent"], "#7C3AED"), key=f"accent_{tn}")

    if any_appearance:
        st.button("↺ Reset appearance", on_click=reset_appearance, width="stretch")
        st.divider()

    st.caption("Conditions to show")
    st.segmented_control("Conditions to show", [3, 5, 7, 10], key="top_k", label_visibility="collapsed")
    st.caption(f"Model: XGBoost · {len(OPTIONS)} symptoms · {len(bundle['classes'])} conditions")

# --------------------------------------------------------------------------- #
# Inject CSS
# --------------------------------------------------------------------------- #
css, colors = build_css(
    cfg,
    st.session_state.theme_name,
    st.session_state.font_name,
    SCALES.get(st.session_state.font_scale) or 1.0,
    RADII.get(st.session_state.radius) or cfg["sizes"]["border_radius_px"],
    primary,
    accent,
)
st.html(f"<style>{css}</style>")

# --------------------------------------------------------------------------- #
# Hero
# --------------------------------------------------------------------------- #
stats = ""
if FEAT["show_hero_stats"]:
    items = [
        (f"{bundle['test_accuracy'] * 100:.1f}%", "Test accuracy"),
        (str(len(bundle["classes"])), "Conditions"),
        (str(len(OPTIONS)), "Symptoms"),
    ]
    stats = "<div class='mp-stats'>" + "".join(
        f"<div class='mp-stat'><b>{v}</b><span>{k}</span></div>" for v, k in items
    ) + "</div>"
st.markdown(
    f"<div class='mp-hero'><h1>{escape(APP['hero_title'])}</h1><p>{escape(APP['hero_subtitle'])}</p>{stats}</div>",
    unsafe_allow_html=True,
)

tab_predict, tab_insights, tab_about = st.tabs(
    [APP["tabs"]["predict"], APP["tabs"]["insights"], APP["tabs"]["about"]]
)

# --------------------------------------------------------------------------- #
# Plot helper (matches the active theme)
# --------------------------------------------------------------------------- #
def themed(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=0, r=10, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=f"{st.session_state.font_name}, sans-serif", color=colors["text"]),
        xaxis=dict(gridcolor=colors["border"], zeroline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", automargin=True),
        showlegend=False,
    )
    return fig


# --------------------------------------------------------------------------- #
# TAB 1 - Diagnose
# --------------------------------------------------------------------------- #
with tab_predict:
    if FEAT["show_disclaimer_banner"]:
        st.markdown(
            f"<div class='mp-notice'><b>{escape(APP['disclaimer_title'])}.</b> {escape(' '.join(APP['disclaimer'].split()))}</div>",
            unsafe_allow_html=True,
        )

    top_k = st.session_state.top_k or 5
    left, right = st.columns([5, 6], gap="large")

    # ---- input card
    with left:
        with st.container(key="card_input"):
            st.markdown("<h3>1 · Select your symptoms</h3>", unsafe_allow_html=True)
            selected = st.multiselect(
                APP["symptom_label"], OPTIONS, key="symptoms",
                format_func=sym_name, placeholder=APP["symptom_placeholder"],
            )
            if FEAT["show_examples"] and cfg.get("examples"):
                st.caption(APP["examples_title"])
                st.pills("Examples", list(cfg["examples"]), key="example_pick",
                         on_change=apply_example, label_visibility="collapsed")

            n = len(selected)
            st.caption(f"{n} symptom{'s' if n != 1 else ''} selected")
            b1, b2 = st.columns([5, 3])
            go_clicked = b1.button(APP["predict_button"], type="primary", width="stretch")
            b2.button(APP["clear_button"], on_click=clear_all, width="stretch")

        if go_clicked:
            if n < PRED["min_symptoms"]:
                st.warning(f"Please select at least {PRED['min_symptoms']} symptoms for a meaningful result.")
            else:
                st.session_state.result = {
                    "selected": list(selected),
                    "top": mu.predict(bundle, selected, top_k=10),
                }

    # ---- result card
    with right:
        res = st.session_state.result
        if not res:
            st.markdown(
                "<div class='mp-card mp-empty'><div class='big'>🩺</div>"
                "<h3>Your results will appear here</h3>"
                "<p>Choose at least a couple of symptoms on the left, then press "
                f"<b>{escape(APP['predict_button'])}</b>.</p></div>",
                unsafe_allow_html=True,
            )
        else:
            top = res["top"][:top_k]
            name, prob = top[0]
            level = mu.confidence_level(prob, cfg)
            level_txt = {"high": "High confidence", "mid": "Moderate confidence", "low": "Low confidence"}[level]

            st.markdown(
                f"<div class='mp-card mp-result'>"
                f"<div class='mp-result-label'>Most likely condition</div>"
                f"<div class='mp-result-name'>{escape(dis_name(name))}</div>"
                f"<span class='mp-badge {level}'>{level_txt} · {prob * 100:.1f}%</span>"
                f"<div class='mp-meter'><div style='width:{prob * 100:.1f}%'></div></div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if set(res["selected"]) != set(selected):
                st.info("Your symptom selection has changed - press the analyse button to update the result.")
            if level == "low":
                st.warning("The model is not confident. Adding more (or more specific) symptoms usually helps.")

            if FEAT["show_probability_chart"]:
                with st.container(key="card_chart"):
                    st.markdown(f"<h3>Top {len(top)} candidates</h3>", unsafe_allow_html=True)
                    labels = [dis_name(d) for d, _ in top][::-1]
                    vals = [p * 100 for _, p in top][::-1]
                    bar_colors = [colors["text_muted"]] * (len(top) - 1) + [colors["primary"]]
                    fig = go.Figure(go.Bar(
                        x=vals, y=labels, orientation="h", marker_color=bar_colors,
                        text=[f"{v:.1f}%" for v in vals], textposition="outside", cliponaxis=False,
                        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
                    ))
                    fig.update_xaxes(range=[0, max(vals) * 1.25 + 5], ticksuffix="%")
                    st.plotly_chart(themed(fig, 70 + 42 * len(top)), width="stretch",
                                    config={"displayModeBar": False})

            if FEAT["show_explanation"]:
                ex = mu.explain(bundle, name, res["selected"])
                with st.expander("Why this result?", expanded=True):
                    if ex["matched"]:
                        st.markdown("**Your symptoms that fit this condition**")
                        st.markdown("".join(f"<span class='mp-chip match'>✓ {escape(sym_name(s))}</span>" for s in ex["matched"]),
                                    unsafe_allow_html=True)
                    if ex["unrelated"]:
                        st.markdown("**Symptoms not typical for it**")
                        st.markdown("".join(f"<span class='mp-chip'>{escape(sym_name(s))}</span>" for s in ex["unrelated"]),
                                    unsafe_allow_html=True)
                    if ex["not_selected"]:
                        st.markdown("**Also common with this condition - do you have these?**")
                        st.markdown("".join(f"<span class='mp-chip missing'>{escape(sym_name(s))}</span>" for s in ex["not_selected"]),
                                    unsafe_allow_html=True)
                        st.caption("Based on how often each symptom appears for this condition in the training data.")

            if FEAT["show_download_button"]:
                st.download_button(
                    "⬇ Download report", mu.build_report(cfg, res["selected"], top),
                    file_name="symptom_report.txt", mime="text/plain",
                )

# --------------------------------------------------------------------------- #
# TAB 2 - Model insights
# --------------------------------------------------------------------------- #
with tab_insights:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Test accuracy", f"{bundle['test_accuracy'] * 100:.2f}%")
    m2.metric("Training rows", f"{bundle['n_train_rows']:,}")
    m3.metric("Symptoms (features)", len(OPTIONS))
    m4.metric("Conditions (classes)", len(bundle["classes"]))
    st.caption(
        f"Accuracy is measured on the {bundle['n_test_rows']} rows of Testing.csv (about one per condition), "
        "so treat it as indicative rather than a guarantee of real-world performance."
    )

    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(key="card_importance"):
            st.markdown("<h3>Most influential symptoms</h3>", unsafe_allow_html=True)
            imp = pd.Series(bundle["feature_importance"]).sort_values(ascending=False).head(15)[::-1]
            fig = go.Figure(go.Bar(
                x=imp.values, y=[sym_name(i) for i in imp.index], orientation="h",
                marker_color=colors["primary"], hovertemplate="%{y}: %{x:.3f}<extra></extra>",
            ))
            st.plotly_chart(themed(fig, 470), width="stretch", config={"displayModeBar": False})
    with c2:
        with st.container(key="card_report"):
            st.markdown("<h3>Per-condition performance</h3>", unsafe_allow_html=True)
            rep = pd.DataFrame(bundle["classification_report"]).T
            rep = rep.loc[[c for c in bundle["classes"] if c in rep.index], ["precision", "recall", "f1-score", "support"]]
            rep.index = [dis_name(i) for i in rep.index]
            body = "".join(
                f"<tr><td>{escape(str(i))}</td><td>{r.precision:.2f}</td><td>{r.recall:.2f}</td>"
                f"<td>{r['f1-score']:.2f}</td><td>{int(r.support)}</td></tr>"
                for i, r in rep.iterrows()
            )
            st.markdown(
                "<div class='mp-table-wrap'><table class='mp-table'><thead><tr><th>Condition</th><th>Precision</th>"
                f"<th>Recall</th><th>F1</th><th>Support</th></tr></thead><tbody>{body}</tbody></table></div>",
                unsafe_allow_html=True,
            )

# --------------------------------------------------------------------------- #
# TAB 3 - About
# --------------------------------------------------------------------------- #
with tab_about:
    a1, a2 = st.columns(2, gap="large")
    with a1:
        with st.container(key="card_about1"):
            st.markdown(
                "<h3>How it works</h3>"
                "<p><b>1.</b> You pick the symptoms you have.<br>"
                f"<b>2.</b> They are converted into a {len(bundle['features'])}-value vector (1 = present, 0 = absent).<br>"
                "<b>3.</b> An XGBoost multi-class classifier returns a probability for every condition.<br>"
                "<b>4.</b> The most probable conditions are shown together with the symptoms that support them.</p>",
                unsafe_allow_html=True,
            )
    with a2:
        with st.container(key="card_about2"):
            st.markdown(
                "<h3>Customising this app</h3>"
                "<p>Every colour, font, size, background, text and feature switch lives in "
                "<code>config.yaml</code>. Edit it, save, and refresh the page. "
                "Visitors can also switch themes, fonts and sizes from the sidebar.</p>",
                unsafe_allow_html=True,
            )
    with st.container(key="card_about3"):
        st.markdown(f"<h3>{escape(APP['disclaimer_title'])}</h3><p>{escape(' '.join(APP['disclaimer'].split()))}</p>",
                    unsafe_allow_html=True)

st.markdown(f"<div class='mp-footer'>{escape(APP['footer'])}</div>", unsafe_allow_html=True)

"""
theme.py - turns config.yaml + the visitor's sidebar choices into one CSS block.

You normally never need to edit this file. Change config.yaml instead.
Only edit this if you want to restyle a *new* Streamlit widget that is not
covered yet.
"""
from __future__ import annotations
import base64
import mimetypes
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _rem(px: float) -> str:
    """px -> rem (relative to 16px) so that the text-size slider scales everything."""
    return f"{px / 16:.4f}rem"


def _font_import(cfg: dict, *font_names: str) -> str:
    fonts = cfg["typography"]["fonts"]
    seen, urls = set(), []
    for name in font_names:
        if name in fonts and name not in seen:
            seen.add(name)
            urls.append(f"@import url('https://fonts.googleapis.com/css2?family={fonts[name]}&display=swap');")
    return "\n".join(urls)


def build_css(
    cfg: dict,
    theme_name: str,
    font_name: str,
    font_scale: float = 1.0,
    radius_px: int | None = None,
    primary: str | None = None,
    accent: str | None = None,
) -> tuple[str, dict]:
    """Return (css_string, resolved_colors)."""
    c = dict(cfg["themes"][theme_name])
    
    # Load a local background image if configured
    background_image_layers = "none"
    image_path = c.get("background_image")

    if image_path:
        image_file = (CONFIG_PATH.parent / image_path).resolve()

        if image_file.is_file():
            mime_type = (
                mimetypes.guess_type(image_file.name)[0]
                or "image/jpeg"
            )
            encoded = base64.b64encode(
                image_file.read_bytes()
            ).decode("utf-8")

            background_image_layers = (
                "linear-gradient(rgba(5,10,25,.72), "
                "rgba(5,10,25,.72)), "
                f"url('data:{mime_type};base64,{encoded}')"
            )
    if primary:
        c["primary"] = primary
    if accent:
        c["accent"] = accent

    s = cfg["sizes"]
    fx = cfg["effects"]
    ty = cfg["typography"]
    radius = s["border_radius_px"] if radius_px is None else radius_px
    heading_font = font_name if ty.get("heading_font", "same") == "same" else ty["heading_font"]
    fallback = ty["fallback"]
    dark = c.get("mode", "light") == "dark"
    sidebar_text = c.get("sidebar_text", c["text"])
    blur = f"blur({fx['glass_blur_px']}px)" if fx.get("glass_blur_px") else "none"
    shadow = (
        "0 10px 30px rgba(0,0,0,.35)" if dark else "0 8px 24px rgba(15,23,42,.08)"
    ) if fx.get("card_shadow") else "none"
    btn_bg = (
        f"linear-gradient(135deg, {c['primary']} 0%, {c['accent']} 100%)"
        if fx.get("button_gradient") else c["primary"]
    )
    html_size = f"{s['base_font_px'] * font_scale:.2f}px"

    anim = ""
    if fx.get("animations"):
        anim = """
        @keyframes mp-fade { from {opacity:0; transform:translateY(8px);} to {opacity:1; transform:none;} }
        .mp-card, .mp-hero, .mp-result { animation: mp-fade .45s ease both; }
        .mp-card:hover { transform: translateY(-2px); }
        .stButton > button:hover { transform: translateY(-1px); }
        """

    css = f"""
{_font_import(cfg, font_name, heading_font)}

:root {{
  --bg: {c['background']};
  --sidebar-bg: {c['sidebar_background']};
  --surface: {c['surface']};
  --surface-alt: {c['surface_alt']};
  --text: {c['text']};
  --muted: {c['text_muted']};
  --border: {c['border']};
  --primary: {c['primary']};
  --primary-contrast: {c['primary_contrast']};
  --accent: {c['accent']};
  --success: {c['success']};
  --warning: {c['warning']};
  --danger: {c['danger']};
  --hero-bg: {c['hero_background']};
  --hero-text: {c['hero_text']};
  --sidebar-text: {sidebar_text};
  --radius: {radius}px;
  --shadow: {shadow};
  --body-font: '{font_name}', {fallback};
  --head-font: '{heading_font}', {fallback};
  color-scheme: {'dark' if dark else 'light'};
}}

html {{ font-size: {html_size}; }}

/* ---------- page ---------- */
.stApp {{
  background-color: var(--bg);
  background-image: {background_image_layers};
  background-size: cover;
  background-position: center center;
  background-repeat: no-repeat;
  background-attachment: fixed;
  color: var(--text);
  font-family: var(--body-font);
}}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stDecoration"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
[data-testid="stToolbarActions"], .stDeployButton {{ display: none !important; }}
/* keep the "open sidebar" arrow visible and styled after the sidebar is collapsed */
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] button {{ color: var(--primary) !important; }}
[data-testid="stExpandSidebarButton"] {{
  display: flex !important; visibility: visible !important; opacity: 1 !important;
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
  box-shadow: var(--shadow);
}}
[data-testid="stExpandSidebarButton"] * {{ color: var(--primary) !important; fill: var(--primary) !important; }}
.block-container {{
  max-width: {s['content_max_width_px']}px;
  padding-top: 2.2rem;
  padding-bottom: 3rem;
}}

/* ---------- typography ---------- */
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea,
.stApp button, .stApp [data-baseweb], .stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stCaptionContainer"] {{
  font-family: var(--body-font);
}}
.stApp p, .stApp li, .stApp label, .stApp span.mp-t,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stWidgetLabel"] p {{
  color: var(--text);
}}
.stApp [data-testid="stCaptionContainer"], .stApp small {{ color: var(--muted); font-size: {_rem(s['small_font_px'])}; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
  font-family: var(--head-font); color: var(--text); letter-spacing: -0.01em;
}}
.stApp h2 {{ font-size: {_rem(s['h2_px'])}; }}
.stApp h3 {{ font-size: {_rem(s['h3_px'])}; }}
/* never touch the icon font */
[data-testid="stIconMaterial"], .material-icons, span[class*="material-symbols"] {{
  font-family: 'Material Symbols Rounded', 'Material Icons' !important;
}}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {{ background: var(--sidebar-bg); border-right: 1px solid var(--border); }}
[data-testid="stSidebar"][aria-expanded="true"] {{
  width: {s['sidebar_width_px']}px !important; min-width: {s['sidebar_width_px']}px !important;
}}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] span.mp-t,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {{ color: var(--sidebar-text); }}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color: var(--sidebar-text); opacity: .75; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(128,128,128,.35); }}

/* ---------- cards / hero ---------- */
.mp-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: {_rem(s['card_padding_px'])};
  box-shadow: var(--shadow);
  backdrop-filter: {blur}; -webkit-backdrop-filter: {blur};
  transition: transform .2s ease;
  margin-bottom: 1rem;
}}
.mp-card h3 {{ margin: 0 0 .35rem 0; font-size: {_rem(s['h3_px'])}; }}
.mp-card .mp-sub {{ color: var(--muted); font-size: {_rem(s['small_font_px'])}; margin: 0 0 .5rem; }}

.mp-hero {{
  background: var(--hero-bg);
  color: var(--hero-text);
  border-radius: calc(var(--radius) + 6px);
  padding: {_rem(s['hero_padding_px'])};
  box-shadow: var(--shadow);
  margin-bottom: 1.2rem;
  position: relative; overflow: hidden;
}}
.mp-hero::after {{
  content: ""; position: absolute; right: -60px; top: -60px; width: 240px; height: 240px;
  border-radius: 50%; background: rgba(255,255,255,.12);
}}
.mp-hero h1 {{
  color: var(--hero-text) !important; font-size: {_rem(s['h1_px'])}; margin: 0 0 .4rem; padding: 0;
  font-family: var(--head-font); font-weight: 800;
}}
.mp-hero p {{ color: var(--hero-text) !important; opacity: .92; max-width: 760px; margin: 0; }}
.mp-stats {{ display: flex; gap: .8rem; flex-wrap: wrap; margin-top: 1.1rem; position: relative; z-index: 1; }}
.mp-stat {{
  background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.28);
  border-radius: var(--radius); padding: .6rem 1.1rem; min-width: 120px; backdrop-filter: blur(6px);
}}
.mp-stat b {{ display: block; font-size: {_rem(s['stat_value_px'])}; color: var(--hero-text); line-height: 1.15; }}
.mp-stat span {{ font-size: {_rem(s['small_font_px'])}; color: var(--hero-text); opacity: .9; }}

/* Streamlit containers created with key="card_..." become cards */
[class*="st-key-card"] {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: {_rem(s['card_padding_px'])};
  box-shadow: var(--shadow);
  backdrop-filter: {blur}; -webkit-backdrop-filter: {blur};
}}
/* pills (quick examples) + segmented controls (sidebar) */
button[data-variant="pills"], button[data-variant="segmented_control"] {{
  background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
  border-radius: calc(var(--radius) * 0.75);
}}
button[data-variant="pills"] {{ border-radius: 999px; }}
button[data-variant="pills"] p, button[data-variant="segmented_control"] p {{
  color: var(--text); font-size: {_rem(s['small_font_px'])};
}}
button[data-variant="pills"]:hover, button[data-variant="segmented_control"]:hover {{ border-color: var(--primary); }}
button[data-variant="pills"][aria-checked="true"], button[data-variant="pills"][aria-pressed="true"],
button[data-variant="pills"][data-selected="true"],
button[data-variant="segmented_control"][aria-checked="true"], button[data-variant="segmented_control"][data-selected="true"] {{
  background: var(--primary) !important; border-color: var(--primary) !important;
}}
button[data-variant][aria-checked="true"] p, button[data-variant][data-selected="true"] p,
button[data-variant="pills"][aria-pressed="true"] p {{ color: var(--primary-contrast) !important; font-weight: 700; }}
[data-testid="stSidebar"] button[data-variant]:not([aria-checked="true"]):not([data-selected="true"]) {{
  background: color-mix(in srgb, var(--sidebar-text) 12%, transparent); border-color: color-mix(in srgb, var(--sidebar-text) 30%, transparent);
}}
[data-testid="stSidebar"] button[data-variant]:not([aria-checked="true"]):not([data-selected="true"]) p {{ color: var(--sidebar-text); }}

/* tab underline + HTML table */
.react-aria-SelectionIndicator {{ background: var(--primary) !important; height: 3px !important; border-radius: 3px; }}
.mp-table-wrap {{ max-height: 430px; overflow: auto; border: 1px solid var(--border); border-radius: calc(var(--radius) / 1.5); }}
.mp-table {{ width: 100%; border-collapse: collapse; font-size: {_rem(s['small_font_px'] + 1)}; color: var(--text); }}
.mp-table th {{ position: sticky; top: 0; background: var(--surface-alt); color: var(--muted); text-align: right; padding: .5rem .7rem; font-weight: 600; }}
.mp-table th:first-child, .mp-table td:first-child {{ text-align: left; min-width: 190px; }}
.mp-table td {{ padding: .42rem .7rem; text-align: right; border-top: 1px solid var(--border); }}
.mp-table tr:hover td {{ background: color-mix(in srgb, var(--primary) 10%, transparent); }}

/* ---------- result ---------- */
.mp-result-label {{ color: var(--muted); font-size: {_rem(s['small_font_px'])}; text-transform: uppercase; letter-spacing: .08em; }}
.mp-result-name {{
  font-family: var(--head-font); font-size: {_rem(s['result_title_px'])}; font-weight: 800;
  color: var(--primary); line-height: 1.15; margin: .15rem 0 .7rem;
}}
.mp-badge {{
  display: inline-block; padding: .25rem .75rem; border-radius: 999px; font-weight: 600;
  font-size: {_rem(s['small_font_px'])}; color: #fff;
}}
.mp-badge.high {{ background: var(--success); }}
.mp-badge.mid {{ background: var(--warning); }}
.mp-badge.low {{ background: var(--danger); }}
.mp-meter {{ height: 12px; background: var(--surface-alt); border-radius: 999px; overflow: hidden; margin: .6rem 0 .3rem; }}
.mp-meter > div {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--primary), var(--accent)); transition: width .8s ease; }}
.mp-chip {{
  display: inline-block; margin: .15rem .25rem .15rem 0; padding: .2rem .7rem; border-radius: 999px;
  background: var(--surface-alt); border: 1px solid var(--border); color: var(--text);
  font-size: {_rem(s['small_font_px'])};
}}
.mp-chip.match {{ background: color-mix(in srgb, var(--success) 18%, transparent); border-color: var(--success); }}
.mp-chip.missing {{ border-style: dashed; color: var(--muted); }}
.mp-notice {{
  border-left: 4px solid var(--warning); background: var(--surface); border-radius: calc(var(--radius) / 2);
  padding: .8rem 1rem; margin: 0 0 1rem; font-size: {_rem(s['small_font_px'] + 1)}; color: var(--text);
  border-top: 1px solid var(--border); border-right: 1px solid var(--border); border-bottom: 1px solid var(--border);
}}
.mp-notice b {{ color: var(--warning); }}
.mp-empty {{ text-align: center; padding: 2.2rem 1rem; color: var(--muted); }}
.mp-empty .big {{ font-size: 2.8rem; }}
.mp-footer {{ text-align: center; color: var(--muted); font-size: {_rem(s['small_font_px'])}; margin-top: 2rem; }}

/* ---------- inputs ---------- */
[data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="textarea"] {{
  background: var(--surface-alt) !important; border-color: var(--border) !important;
  border-radius: var(--radius) !important; color: var(--text) !important;
}}
[data-baseweb="select"] input, [data-baseweb="input"] input {{ color: var(--text) !important; -webkit-text-fill-color: var(--text); }}
[data-baseweb="select"] svg {{ fill: var(--muted); }}
[data-tag], [data-baseweb="tag"] {{
  background: var(--primary) !important; color: var(--primary-contrast) !important;
  border-radius: calc(var(--radius) / 1.6) !important;
}}
[data-tag] *, [data-baseweb="tag"] * {{ color: var(--primary-contrast) !important; fill: var(--primary-contrast) !important; }}
/* react-aria based select / multiselect (Streamlit >= 1.5x) */
[data-testid="stMultiSelect"] [role="group"], [data-testid="stSelectbox"] [role="group"],
[data-testid="stSelectbox"] [data-testid="stSelectboxField"], [data-testid="stNumberInput"] [role="group"],
[data-testid="stTextInput"] [role="group"] {{
  background: var(--surface-alt) !important; border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important; color: var(--text) !important;
}}
[data-testid="stMultiSelect"] input, [data-testid="stSelectbox"] input, [data-testid="stSelectbox"] [role="combobox"] {{
  color: var(--text) !important; -webkit-text-fill-color: var(--text); background: transparent !important;
}}
[data-testid="stMultiSelect"] input::placeholder {{ color: var(--muted) !important; -webkit-text-fill-color: var(--muted); }}
[data-testid="stMultiSelect"] svg, [data-testid="stSelectbox"] svg {{ color: var(--muted); fill: var(--muted); }}
[data-testid$="Dropdown"], [data-testid$="Dropdown"] [role="listbox"] {{
  background: var(--surface-alt) !important; border-radius: var(--radius) !important; border: 1px solid var(--border);
}}
[role="option"], [role="option"] * {{ color: var(--text) !important; }}
[role="option"][aria-selected="true"], [role="option"]:hover {{ background: color-mix(in srgb, var(--primary) 22%, transparent) !important; }}
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"], [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-testid="stSelectboxField"] {{
  background: color-mix(in srgb, var(--sidebar-text) 12%, transparent) !important;
  border-color: color-mix(in srgb, var(--sidebar-text) 30%, transparent) !important;
}}
[data-testid="stSidebar"] [data-testid="stSelectbox"] * {{ color: var(--sidebar-text) !important; -webkit-text-fill-color: var(--sidebar-text); }}
[data-testid="stSidebar"] [data-testid="stSelectbox"] svg {{ fill: var(--sidebar-text); }}
/* dropdown pop-overs are rendered outside .stApp */
[data-baseweb="popover"] > div, [data-baseweb="menu"], ul[role="listbox"] {{
  background: var(--surface-alt) !important; color: var(--text) !important; border-radius: var(--radius) !important;
}}
[data-baseweb="popover"] li, [data-baseweb="menu"] li {{ color: var(--text) !important; background: transparent !important; }}
[data-baseweb="popover"] li:hover, [data-baseweb="menu"] li:hover,
[data-baseweb="popover"] li[aria-selected="true"] {{ background: color-mix(in srgb, var(--primary) 22%, transparent) !important; }}
[data-testid="stSidebar"] [data-baseweb="select"] > div {{ background: rgba(255,255,255,.14) !important; border-color: rgba(255,255,255,.3) !important; }}
[data-testid="stSidebar"] [data-baseweb="select"] div, [data-testid="stSidebar"] [data-baseweb="select"] input {{
  color: var(--sidebar-text) !important; -webkit-text-fill-color: var(--sidebar-text);
}}
[data-testid="stSidebar"] [data-baseweb="select"] svg {{ fill: var(--sidebar-text); }}

/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button {{
  border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface);
  color: var(--text); font-weight: 600; padding: .55rem 1.1rem; transition: all .2s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color: var(--primary); color: var(--primary); }}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
  background: {btn_bg}; color: var(--primary-contrast); border: none; box-shadow: var(--shadow);
}}
.stButton > button[kind="primary"] p {{ color: var(--primary-contrast) !important; }}
.stButton > button[kind="primary"]:hover {{ filter: brightness(1.08); color: var(--primary-contrast); }}
[data-testid="stSidebar"] .stButton > button {{ background: color-mix(in srgb, var(--sidebar-text) 12%, transparent); color: var(--sidebar-text); border-color: color-mix(in srgb, var(--sidebar-text) 30%, transparent); }}
[data-testid="stSidebar"] .stButton > button p {{ color: var(--sidebar-text) !important; }}

/* ---------- tabs / expander / slider / misc ---------- */
.stTabs [data-baseweb="tab-list"] {{ gap: .4rem; border-bottom: 1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{ border-radius: var(--radius) var(--radius) 0 0; color: var(--muted); padding: .6rem 1.1rem; }}
.stTabs [aria-selected="true"] {{ color: var(--primary) !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: var(--primary); height: 3px; border-radius: 3px; }}
[data-testid="stExpander"] {{
  background: var(--surface); border: 1px solid var(--border) !important; border-radius: var(--radius);
}}
[data-testid="stExpander"] summary p {{ color: var(--text); font-weight: 600; }}
[data-testid="stSidebar"] [data-testid="stExpander"] {{ background: color-mix(in srgb, var(--sidebar-text) 8%, transparent); border-color: color-mix(in srgb, var(--sidebar-text) 25%, transparent) !important; }}
[data-testid="stMetric"] {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: .8rem 1rem; }}
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] p {{ color: var(--text); }}
[data-testid="stDataFrame"] {{ border-radius: var(--radius); overflow: hidden; border: 1px solid var(--border); }}
[data-testid="stAlert"] {{ border-radius: var(--radius); }}
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-thumb {{ background: color-mix(in srgb, var(--muted) 45%, transparent); border-radius: 10px; }}
{anim}

/* hide default Streamlit chrome */
#MainMenu, footer {{ visibility: hidden; }}
"""
    return css, c

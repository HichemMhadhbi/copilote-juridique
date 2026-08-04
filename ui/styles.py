"""Theme visuel professionnel - TOP-JURIDIQUE."""

import streamlit as st

COLORS = {
    "navy": "#16213E",
    "navy_light": "#243A63",
    "gold": "#B8956A",
    "gold_light": "#D8C3A5",
    "bg": "#F3F5F9",
    "white": "#FFFFFF",
    "text": "#1C2333",
    "text_muted": "#5D6B82",
    "border": "#E1E6EE",
    "success": "#1E7A46",
    "danger": "#C0392B",
    "warning": "#C77D2E",
    "info": "#2C5F9E",
}


def inject_global_styles():
    """Injection du theme via st.html (rendu brut, hors pipeline Markdown).

    Le CSS DOIT etre re-emis a chaque rerun : Streamlit supprime a la fin de
    chaque execution les elements qui n'ont pas ete re-emis. Un garde en
    session_state ferait disparaitre le theme apres la premiere interaction.
    """
    st.html(
        """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
<style>
:root {
    --legal-navy: #16213E;
    --legal-navy-light: #243A63;
    --legal-gold: #B8956A;
    --legal-gold-light: #D8C3A5;
    --legal-bg: #F3F5F9;
    --legal-white: #FFFFFF;
    --legal-text: #1C2333;
    --legal-muted: #5D6B82;
    --legal-border: #E1E6EE;
    --legal-success: #1E7A46;
    --legal-danger: #C0392B;
    --legal-warning: #C77D2E;
    --legal-info: #2C5F9E;
}

/* ---------- Global ---------- */
html, body, .stApp {
    background-color: var(--legal-bg);
    color: var(--legal-text);
    font-family: 'Inter', sans-serif;
}
.stApp { background: linear-gradient(180deg, #F7F8FB 0%, var(--legal-bg) 240px); }

h1, h2, h3, h4 {
    font-family: 'Playfair Display', serif !important;
    color: var(--legal-navy) !important;
    letter-spacing: -0.01em;
}
.block-container { padding-top: 2.2rem; max-width: 1200px; }
[data-testid="stCaptionContainer"] p { color: var(--legal-muted); font-size: 0.82rem; }
[data-testid="stMarkdownContainer"] p { line-height: 1.6; }

/* Hide default menu / footer */
#MainMenu, footer, [data-testid="stStatusWidget"], [data-testid="stToolbar"] { visibility: hidden; height: 0; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background-color: var(--legal-white);
    border-right: 1px solid var(--legal-border);
}
[data-testid="stSidebar"] .block-container { padding-top: 0; }
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] { background: transparent; }
[data-testid="stSidebar"] h3 { font-family: 'Inter', sans-serif !important; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--legal-muted) !important; margin-top: 0.8rem; }
[data-testid="stSidebar"] hr { border-color: var(--legal-border); }

/* ---------- Buttons ---------- */
.stButton > button {
    border-radius: 10px;
    border: 1px solid var(--legal-border);
    background-color: var(--legal-white);
    color: var(--legal-navy);
    font-weight: 600;
    font-family: 'Inter', sans-serif;
    padding: 0.6rem 1rem;
    transition: all 0.18s ease;
}
.stButton > button:hover {
    border-color: var(--legal-gold);
    color: var(--legal-navy);
    box-shadow: 0 3px 10px rgba(22, 33, 62, 0.10);
}
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, var(--legal-navy) 0%, var(--legal-navy-light) 100%) !important;
    border: none !important;
    color: #fff !important;
}
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(135deg, var(--legal-navy-light) 0%, #31508a 100%) !important;
    box-shadow: 0 6px 16px rgba(22, 33, 62, 0.28) !important;
    transform: translateY(-1px);
}
.stDownloadButton > button {
    border-radius: 10px;
    border: 1px solid var(--legal-gold) !important;
    background: linear-gradient(135deg, #FFF 0%, #F7F2EA 100%) !important;
    color: var(--legal-navy) !important;
    font-weight: 700 !important;
    font-family: 'Inter', sans-serif;
}
.stDownloadButton > button:hover {
    box-shadow: 0 4px 14px rgba(184, 149, 106, 0.35);
}

/* ---------- File uploader ---------- */
[data-testid="stFileUploaderDropzone"] {
    border: 2px dashed var(--legal-gold) !important;
    border-radius: 14px;
    background: #FBF8F2 !important;
    transition: all 0.2s ease;
}
[data-testid="stFileUploaderDropzone"]:hover {
    background: #F7F0E4 !important;
    border-color: var(--legal-gold-light) !important;
}
[data-testid="stFileUploaderDropzone"] small, [data-testid="stFileUploaderDropzoneInstructions"] div {
    color: var(--legal-navy) !important;
}
[data-testid="stFileUploaderFile"] {
    border-radius: 10px;
    border: 1px solid var(--legal-border);
}

/* ---------- Pills / mode selector ---------- */
[data-testid="stPills"] {
    gap: 0.5rem;
}
[data-testid="stPills"] label {
    border: 1px solid var(--legal-border) !important;
    border-radius: 999px !important;
    background: var(--legal-white) !important;
    color: var(--legal-navy) !important;
    font-weight: 600 !important;
    padding: 0.45rem 1.1rem !important;
    transition: all 0.15s ease;
}
[data-testid="stPills"] label:hover { border-color: var(--legal-gold) !important; }
[data-testid="stPills"] label[aria-checked="true"],
[data-testid="stPills"] label[data-checked="true"] {
    background: linear-gradient(135deg, var(--legal-navy), var(--legal-navy-light)) !important;
    color: #fff !important;
    border-color: var(--legal-navy) !important;
}

/* ---------- Radio ---------- */
[data-testid="stRadio"] [role="radiogroup"] { gap: 0.3rem; }
[data-testid="stRadio"] label {
    border-radius: 8px;
    padding: 0.35rem 0.6rem;
    color: var(--legal-text);
}

/* ---------- Selectbox ---------- */
[data-baseweb="select"] > div {
    border-radius: 10px !important;
    border-color: var(--legal-border) !important;
    font-family: 'Inter', sans-serif;
}

/* ---------- Metrics ---------- */
[data-testid="stMetric"] {
    background: var(--legal-white);
    border: 1px solid var(--legal-border);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow: 0 1px 3px rgba(22, 33, 62, 0.05);
}
[data-testid="stMetricLabel"] p { color: var(--legal-muted) !important; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; }
[data-testid="stMetricValue"] { font-family: 'Playfair Display', serif !important; color: var(--legal-navy) !important; }

/* ---------- Expander ---------- */
details[data-testid="stExpander"] {
    background: var(--legal-white);
    border: 1px solid var(--legal-border);
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(22, 33, 62, 0.04);
}
details[data-testid="stExpander"] summary { font-weight: 600; color: var(--legal-navy); }

/* ---------- Alerts ---------- */
[data-testid="stAlert"] {
    border-radius: 12px;
    border-left-width: 4px;
}

/* ---------- Chat input ---------- */
[data-testid="stChatInput"] {
    border-radius: 14px !important;
    border: 1px solid var(--legal-border) !important;
    box-shadow: 0 2px 8px rgba(22, 33, 62, 0.06) !important;
}
[data-testid="stChatInput"]:focus-within { border-color: var(--legal-gold) !important; }

/* ---------- Tabs / dividers ---------- */
[data-testid="stDivider"] { border-color: var(--legal-border); }
[data-testid="stTab"] button { font-family: 'Inter', sans-serif; font-weight: 600; }

/* ---------- Tables ---------- */
[data-testid="stTable"] { border-radius: 10px; overflow: hidden; }

/* ---------- Scrollbar ---------- */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: #C9D1DE; border-radius: 6px; }
::-webkit-scrollbar-track { background: transparent; }

/* ---------- Composants TOP-JURIDIQUE ---------- */

/* Hero */
.tj-hero {
    background: linear-gradient(135deg, #16213E 0%, #243A63 60%, #31508A 100%);
    border-radius: 18px;
    padding: 2.2rem 2.4rem 1.9rem 2.4rem;
    color: #fff;
    box-shadow: 0 10px 30px rgba(22, 33, 62, 0.28);
    position: relative;
    overflow: hidden;
    margin-bottom: 1.6rem;
}
.tj-hero::after {
    content: "";
    position: absolute;
    top: -60px; right: -40px;
    width: 280px; height: 280px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(184,149,106,0.35) 0%, transparent 70%);
}
.tj-hero h1 {
    color: #fff !important;
    font-size: 2.1rem;
    margin: 0 0 0.4rem 0;
    font-family: 'Playfair Display', serif !important;
    letter-spacing: -0.01em;
}
.tj-hero p { color: #D8E1F0; margin: 0; font-size: 1.02rem; max-width: 640px; }
.tj-brand {
    display: flex; align-items: center; gap: 0.65rem;
    font-family: 'Inter', sans-serif;
    font-weight: 700; font-size: 0.8rem;
    letter-spacing: 0.22em; text-transform: uppercase;
    color: #D8C3A5;
    margin-bottom: 0.9rem;
}
.tj-logo {
    display: inline-flex; align-items: center; justify-content: center;
    width: 34px; height: 34px; border-radius: 9px;
    background: rgba(184,149,106,0.22);
    border: 1px solid rgba(216,195,165,0.55);
    font-size: 1.05rem;
}

/* Sidebar brand */
.tj-sidebar-brand {
    background: linear-gradient(135deg, #16213E, #243A63);
    border-radius: 0 0 14px 14px;
    padding: 1.3rem 1.2rem 1.1rem 1.2rem;
    color: #fff;
    margin: -0rem -1rem 1.2rem -1rem;
}
.tj-sidebar-brand .tj-logo { background: rgba(184,149,106,0.25); }
.tj-sidebar-brand .tj-brand { margin-bottom: 0.4rem; color: #D8C3A5; font-size: 0.72rem; }
.tj-sidebar-brand h2 {
    color: #fff !important;
    font-size: 1.25rem; margin: 0 0 0.2rem 0;
    font-family: 'Playfair Display', serif !important;
}
.tj-sidebar-brand p { color: #C7D2E5; font-size: 0.82rem; margin: 0; }

/* Section titles */
.tj-section-title { display: flex; align-items: flex-start; gap: 0.7rem; margin: 1.1rem 0 0.3rem 0; }
.tj-section-accent { width: 5px; height: 34px; border-radius: 3px; background: linear-gradient(180deg, #B8956A, #D8C3A5); flex: 0 0 auto; }
.tj-section-title h2 { margin: 0; font-size: 1.45rem; line-height: 1.25; }
.tj-section-title p { margin: 0.15rem 0 0 0; color: #5D6B82; font-size: 0.9rem; }

/* Status banner */
.tj-status {
    display: flex; align-items: center; gap: 0.6rem;
    background: #fff;
    border: 1px solid var(--legal-border);
    border-left: 4px solid var(--legal-gold);
    border-radius: 12px;
    padding: 0.7rem 1rem;
    margin: 0 0 1rem 0;
    box-shadow: 0 1px 3px rgba(22,33,62,0.05);
    font-size: 0.92rem;
}
.tj-status.ok { border-left-color: var(--legal-success); }
.tj-status.wait { border-left-color: var(--legal-warning); }
.tj-status-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--legal-gold); flex: 0 0 auto; }
.tj-status.ok .tj-status-dot { background: var(--legal-success); box-shadow: 0 0 0 4px rgba(30,122,70,0.12); }
.tj-status.wait .tj-status-dot { background: var(--legal-warning); box-shadow: 0 0 0 4px rgba(199,125,46,0.12); }

/* Badges */
.tj-badge {
    display: inline-block;
    padding: 0.28rem 0.85rem;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.78rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-family: 'Inter', sans-serif;
}
.tj-badge.eleve { background: #FDECEA; color: #C0392B; border: 1px solid #F5C6C0; }
.tj-badge.moderate { background: #FDF3E7; color: #C77D2E; border: 1px solid #F0D6AC; }
.tj-badge.faible { background: #E8F5EE; color: #1E7A46; border: 1px solid #BFE3CD; }
.tj-badge.non-evalue { background: #EEF1F6; color: #5D6B82; border: 1px solid #D8DEE8; }

/* KPI cards */
.tj-kpi {
    background: #fff;
    border: 1px solid var(--legal-border);
    border-radius: 14px;
    padding: 1.05rem 1.15rem;
    box-shadow: 0 1px 3px rgba(22,33,62,0.05);
}
.tj-kpi .kpi-label { color: var(--legal-muted); font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
.tj-kpi .kpi-value { font-family: 'Playfair Display', serif; font-size: 1.7rem; font-weight: 700; color: var(--legal-navy); line-height: 1.15; margin: 0.2rem 0 0.15rem 0; }
.tj-kpi .kpi-sub { color: var(--legal-muted); font-size: 0.78rem; }

/* Cards generiques */
.tj-card {
    background: #fff;
    border: 1px solid var(--legal-border);
    border-radius: 14px;
    padding: 1.15rem 1.3rem;
    box-shadow: 0 1px 3px rgba(22,33,62,0.05);
    margin-bottom: 0.9rem;
}

/* Entities */
.tj-entity-block { margin-bottom: 0.7rem; }
.tj-entity-label { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--legal-muted); display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.45rem; }
.tj-entity-label .tj-entity-icon { font-size: 0.95rem; }
.tj-entity-pills { display: flex; flex-wrap: wrap; gap: 0.45rem; }
.tj-pill {
    display: inline-flex; align-items: center; gap: 0.35rem;
    background: #F4F6FB; border: 1px solid #E1E6EE;
    color: #1C2333; border-radius: 999px;
    padding: 0.3rem 0.85rem; font-size: 0.88rem; font-weight: 600;
}
.tj-pill.gold { background: #FBF7EF; border-color: #E7D5B8; }
.tj-empty { color: var(--legal-muted); font-size: 0.88rem; font-style: italic; }

/* Chat */
.tj-chat-row { display: flex; gap: 0.6rem; margin-bottom: 1rem; align-items: flex-start; }
.tj-chat-row.user { justify-content: flex-end; }
.tj-avatar {
    width: 38px; height: 38px; border-radius: 12px; flex: 0 0 auto;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 1.1rem;
}
.tj-avatar.assistant { background: linear-gradient(135deg, #16213E, #243A63); box-shadow: 0 2px 6px rgba(22,33,62,0.25); }
.tj-avatar.user { background: linear-gradient(135deg, #B8956A, #C9A87F); box-shadow: 0 2px 6px rgba(184,149,106,0.30); }
.tj-bubble {
    max-width: 82%;
    border-radius: 16px;
    padding: 0.8rem 1.05rem;
    font-size: 0.94rem;
    line-height: 1.6;
    box-shadow: 0 1px 4px rgba(22,33,62,0.07);
}
.tj-bubble.assistant { background: #fff; border: 1px solid var(--legal-border); border-top-left-radius: 4px; color: var(--legal-text); }
.tj-bubble.user { background: linear-gradient(135deg, #16213E, #243A63); color: #fff; border-top-right-radius: 4px; }
.tj-bubble .tj-time { font-size: 0.72rem; opacity: 0.62; margin-top: 0.5rem; text-align: right; }
.tj-bubble strong { font-weight: 700; }
.tj-bubble.assistant blockquote {
    margin: 0.4rem 0; padding: 0.4rem 0.7rem;
    border-left: 3px solid var(--legal-gold);
    background: #FBF7EF; border-radius: 0 8px 8px 0;
    color: #3A4557; font-size: 0.9rem;
}
.tj-bubble hr { border: 0; border-top: 1px solid var(--legal-border); margin: 0.6rem 0; }
.tj-bubble code { background: #EEF1F6; padding: 0.1rem 0.35rem; border-radius: 5px; font-size: 0.85em; }
</style>
        """
    )

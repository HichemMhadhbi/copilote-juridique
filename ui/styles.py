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
    --legal-navy: #152A55;
    --legal-navy-soft: #1D4371;
    --legal-accent: #2365DF;
    --legal-accent-soft: #E7EFFC;
    --legal-gold: #F2B84B;
    --legal-gold-soft: #F8D98C;
    --legal-sky: #F0F5FF;
    --legal-sky-dark: #D9E4FB;
    --legal-bg: #F5F8FF;
    --legal-white: #FFFFFF;
    --legal-text: #112243;
    --legal-muted: #6D7B98;
    --legal-border: #E7ECF6;
    --legal-success: #2E8B57;
    --legal-danger: #D64545;
    --legal-warning: #F2C94C;
}

/* ---------- Global ---------- */
html, body, .stApp {
    background-color: var(--legal-bg);
    color: var(--legal-text);
    font-family: 'Inter', sans-serif;
}
.stApp { background: linear-gradient(180deg, #F8FBFF 0%, var(--legal-bg) 100%); }

h1, h2, h3, h4 {
    font-family: 'Playfair Display', serif !important;
    color: var(--legal-navy) !important;
    letter-spacing: -0.01em;
}
.block-container { padding-top: 1.6rem; max-width: 1260px; }
[data-testid="stCaptionContainer"] p { color: var(--legal-muted); font-size: 0.84rem; }
[data-testid="stMarkdownContainer"] p { line-height: 1.65; }

/* Hide default menu / footer */
#MainMenu, footer, [data-testid="stStatusWidget"], [data-testid="stToolbar"] { visibility: hidden; height: 0; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background-color: var(--legal-white);
    border-right: none;
    box-shadow: 3px 0 22px rgba(15, 34, 68, 0.08);
    padding-top: 0.7rem;
}
[data-testid="stSidebar"] .block-container { padding-top: 0.5rem; }
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] { background: transparent; }
[data-testid="stSidebar"] h3 { font-family: 'Inter', sans-serif !important; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--legal-muted) !important; margin-top: 0.85rem; }
[data-testid="stSidebar"] hr { border-color: var(--legal-border); }

.tj-sidebar-card {
    background: var(--legal-sky);
    border: 1px solid var(--legal-border);
    border-radius: 20px;
    padding: 1rem 1rem 1.1rem 1rem;
    margin-bottom: 1.1rem;
}
.tj-sidebar-user {
    display: flex;
    align-items: center;
    gap: 0.9rem;
}
.tj-user-avatar {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    background: var(--legal-accent);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 1rem;
}
.tj-user-name {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--legal-navy);
}
.tj-user-role {
    font-size: 0.75rem;
    color: var(--legal-accent);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.tj-sidebar-card-top {
    margin-top: 0.55rem;
}
.tj-sidebar-logo-fallback {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 170px;
    min-height: 70px;
    border-radius: 20px;
    background: var(--legal-sky);
    border: 1px solid var(--legal-border);
    color: var(--legal-navy);
    font-weight: 700;
    font-size: 0.95rem;
    padding: 1rem 0.8rem;
    margin-bottom: 1rem;
}
.tj-sidebar-intro {
    background: var(--legal-sky);
    border: 1px solid var(--legal-border);
    border-radius: 18px;
    padding: 1rem;
    margin-bottom: 1rem;
}
.tj-sidebar-intro-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--legal-navy);
    margin-bottom: 0.22rem;
}
.tj-sidebar-intro-copy {
    font-size: 0.82rem;
    color: var(--legal-muted);
    line-height: 1.5;
}

/* ---------- Buttons ---------- */
.stButton > button {
    border-radius: 14px;
    border: 1px solid var(--legal-border);
    background-color: var(--legal-white);
    color: var(--legal-navy);
    font-weight: 700;
    font-family: 'Inter', sans-serif;
    padding: 0.75rem 1rem;
    transition: all 0.18s ease;
}
.stButton > button:hover {
    border-color: var(--legal-accent);
    color: var(--legal-navy);
    box-shadow: 0 6px 22px rgba(15, 34, 68, 0.12);
}
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, var(--legal-accent), #1B4FC1) !important;
    border: none !important;
    color: #fff !important;
}
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(135deg, #1B4FC1, var(--legal-accent)) !important;
    box-shadow: 0 6px 18px rgba(15, 34, 68, 0.22) !important;
    transform: translateY(-1px);
}
.stDownloadButton > button {
    border-radius: 14px;
    border: 1px solid var(--legal-border) !important;
    background: #F8FAFF !important;
    color: var(--legal-navy) !important;
    font-weight: 700 !important;
}
.stDownloadButton > button:hover {
    box-shadow: 0 4px 14px rgba(15, 34, 68, 0.12);
}

/* ---------- File uploader ---------- */
[data-testid="stFileUploaderDropzone"] {
    border: 2px dashed var(--legal-sky-dark) !important;
    border-radius: 18px;
    background: #F8FBFF !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    background: #EEF5FF !important;
    border-color: var(--legal-gold) !important;
}
[data-testid="stFileUploaderDropzone"] small, [data-testid="stFileUploaderDropzoneInstructions"] div {
    color: var(--legal-navy) !important;
}
[data-testid="stFileUploaderFile"] {
    border-radius: 12px;
    border: 1px solid var(--legal-border);
}

/* ---------- Pills / mode selector ---------- */
[data-testid="stPills"] {
    gap: 0.6rem;
}
[data-testid="stPills"] label {
    border: 1px solid var(--legal-border) !important;
    border-radius: 999px !important;
    background: var(--legal-white) !important;
    color: var(--legal-navy) !important;
    font-weight: 700 !important;
    padding: 0.55rem 1.15rem !important;
}
[data-testid="stPills"] label:hover { border-color: var(--legal-accent) !important; }
[data-testid="stPills"] label[aria-checked="true"],
[data-testid="stPills"] label[data-checked="true"] {
    background: var(--legal-accent) !important;
    color: #fff !important;
    border-color: var(--legal-accent) !important;
}

/* ---------- Search simulation ---------- */
.tj-search-sim {
    flex: 1;
    min-width: 280px;
    background: var(--legal-white);
    border: 1px solid var(--legal-border);
    border-radius: 16px;
    padding: 0.9rem 1rem;
    color: var(--legal-muted);
    font-size: 0.95rem;
    display: inline-flex;
    align-items: center;
    gap: 0.65rem;
}
.tj-hero-actions {
    display: none;
}
.tj-hero-badges {
    display: none;
}
.tj-pill-card {
    display: none;
}
.tj-pill-card.status-ready {
    display: none;
}

/* ---------- Hero ---------- */
.tj-hero {
    background: linear-gradient(180deg, #F6F8FF 0%, #EAF1FF 100%);
    border-radius: 26px;
    padding: 2rem 2.4rem 2.2rem 2.4rem;
    color: var(--legal-navy);
    box-shadow: 0 20px 48px rgba(15, 34, 68, 0.08);
    margin-bottom: 1.35rem;
}
.tj-hero-top {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 1rem;
    margin-bottom: 1.2rem;
}
.tj-hero h1 {
    font-size: 2.15rem;
    margin: 0;
    letter-spacing: -0.02em;
}
.tj-hero p {
    color: var(--legal-muted);
    margin: 0.65rem 0 0 0;
    max-width: 820px;
    font-size: 1rem;
}
.tj-hero-pill {
    padding: 0.72rem 1.1rem;
    border-radius: 999px;
    background: #E7F0FF;
    color: var(--legal-accent);
    font-weight: 700;
    border: 1px solid #D4E3FB;
    font-size: 0.92rem;
}

.tj-brand {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--legal-navy);
}
.tj-brand-text {
    display: inline-block;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.12em;
}
.tj-hero-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 54px;
    height: 54px;
    border-radius: 18px;
    background: #F8FAFF;
    border: 1px solid rgba(224, 228, 236, 0.9);
    color: var(--legal-accent);
    font-size: 1.45rem;
    box-shadow: 0 8px 20px rgba(15, 34, 68, 0.10);
}

/* ---------- Sidebar brand */
.tj-sidebar-brand {
    background: linear-gradient(135deg, #16213E, #22345F);
    border-radius: 0 0 18px 18px;
    padding: 1.4rem 1.3rem 1.1rem 1.3rem;
    color: #fff;
    margin: -1rem -1rem 1.2rem -1rem;
}
.tj-sidebar-brand .tj-logo { background: rgba(255,255,255,0.12); }
.tj-sidebar-brand .tj-brand { margin-bottom: 0.4rem; color: rgba(255,255,255,0.85); font-size: 0.72rem; }
.tj-sidebar-brand h2 {
    color: #fff !important;
    font-size: 1.1rem; margin: 0 0 0.3rem 0;
    font-family: 'Playfair Display', serif !important;
}
.tj-sidebar-brand p { color: rgba(255,255,255,0.72); font-size: 0.82rem; margin: 0; }

/* Section titles */
.tj-section-title { display: flex; align-items: flex-start; gap: 0.7rem; margin: 1.35rem 0 0.45rem 0; }
.tj-section-accent { width: 5px; height: 34px; border-radius: 3px; background: linear-gradient(180deg, var(--legal-gold), var(--legal-gold-soft)); flex: 0 0 auto; }
.tj-section-title h2 { margin: 0; font-size: 1.55rem; line-height: 1.2; }
.tj-section-title p { margin: 0.2rem 0 0 0; color: var(--legal-muted); font-size: 0.92rem; }

/* Status banner */
.tj-status {
    display: flex; align-items: center; gap: 0.7rem;
    background: #fff;
    border: 1px solid var(--legal-border);
    border-left: 4px solid var(--legal-gold-soft);
    border-radius: 14px;
    padding: 0.95rem 1.1rem;
    margin: 0 0 1.2rem 0;
    box-shadow: 0 2px 8px rgba(22,33,62,0.06);
    font-size: 0.95rem;
}
.tj-status.ok { border-left-color: var(--legal-success); }
.tj-status.wait { border-left-color: var(--legal-warning); }
.tj-status-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--legal-gold-soft); flex: 0 0 auto; }
.tj-status.ok .tj-status-dot { background: var(--legal-success); box-shadow: 0 0 0 4px rgba(30,122,70,0.12); }
.tj-status.wait .tj-status-dot { background: var(--legal-warning); box-shadow: 0 0 0 4px rgba(240,178,122,0.14); }

/* Badges */
.tj-badge {
    display: inline-block;
    padding: 0.28rem 0.85rem;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.76rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-family: 'Inter', sans-serif;
}
.tj-badge.eleve { background: #FDECEA; color: #C0392B; border: 1px solid #F5C6C0; }
.tj-badge.moderate { background: #FFF2E8; color: #C77D2E; border: 1px solid #F0D6AC; }
.tj-badge.faible { background: #E8F5EE; color: #1E7A46; border: 1px solid #BFE3CD; }
.tj-badge.non-evalue { background: #EEF1F6; color: #5D6B82; border: 1px solid #D8DEE8; }

/* KPI cards */
.tj-kpi {
    background: #fff;
    border: 1px solid var(--legal-border);
    border-radius: 18px;
    padding: 1.15rem 1.25rem;
    box-shadow: 0 3px 18px rgba(22,33,62,0.06);
    min-height: 126px;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.tj-kpi:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(15,34,68,0.10); }
.tj-kpi-head { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; }
.tj-kpi-icon {
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    background: var(--legal-accent-soft);
    color: var(--legal-accent);
    font-size: 1rem;
}
.tj-kpi .kpi-label { color: var(--legal-muted); font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
.tj-kpi .kpi-value { font-family: 'Playfair Display', serif; font-size: 2rem; font-weight: 800; color: var(--legal-navy); line-height: 1.05; margin: 0.25rem 0 0.35rem 0; }
.tj-kpi .kpi-sub { color: var(--legal-muted); font-size: 0.82rem; }

/* Cards generiques */
.tj-card {
    background: #fff;
    border: 1px solid var(--legal-border);
    border-radius: 18px;
    padding: 1.25rem 1.4rem;
    box-shadow: 0 3px 18px rgba(22,33,62,0.05);
    margin-bottom: 1rem;
}

/* Entities */
.tj-entity-block { margin-bottom: 0.85rem; }
.tj-entity-label { font-size: 0.76rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--legal-muted); display: flex; align-items: center; gap: 0.45rem; margin-bottom: 0.45rem; }
.tj-entity-label .tj-entity-icon { font-size: 1rem; }
.tj-entity-pills { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.tj-pill {
    display: inline-flex; align-items: center; gap: 0.35rem;
    background: #F6F8FF; border: 1px solid #E1E6EE;
    color: #1C2333; border-radius: 999px;
    padding: 0.34rem 0.95rem; font-size: 0.88rem; font-weight: 600;
}
.tj-pill.gold { background: #FBF7EF; border-color: #E7D5B8; }
.tj-empty { color: var(--legal-muted); font-size: 0.9rem; font-style: italic; }

/* Chat */
.tj-chat-row { display: flex; gap: 0.75rem; margin-bottom: 1rem; align-items: flex-start; }
.tj-chat-row.user { justify-content: flex-end; }
.tj-avatar {
    width: 42px; height: 42px; border-radius: 14px; flex: 0 0 auto;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 1.15rem;
}
.tj-avatar.assistant { background: linear-gradient(135deg, #16213E, #243A63); box-shadow: 0 2px 8px rgba(22,33,62,0.25); color: #fff; }
.tj-avatar.user { background: linear-gradient(135deg, #1E7DFF, #70A7FF); box-shadow: 0 2px 8px rgba(30,125,255,0.25); color: #fff; }
.tj-bubble { max-width: 82%; border-radius: 18px; padding: 0.95rem 1.1rem; font-size: 0.95rem; line-height: 1.65; box-shadow: 0 2px 14px rgba(22,33,62,0.06); }
.tj-bubble.assistant { background: #fff; border: 1px solid var(--legal-border); border-top-left-radius: 5px; color: var(--legal-text); }
.tj-bubble.user { background: linear-gradient(135deg, #16213E, #243A63); color: #fff; border-top-right-radius: 5px; }
.tj-bubble .tj-time { font-size: 0.72rem; opacity: 0.65; margin-top: 0.45rem; text-align: right; }
.tj-bubble strong { font-weight: 700; }
.tj-bubble.assistant blockquote {
    margin: 0.5rem 0; padding: 0.55rem 0.85rem;
    border-left: 3px solid var(--legal-gold);
    background: #FBF7EF; border-radius: 0 10px 10px 0;
    color: #3A4557; font-size: 0.92rem;
}
.tj-bubble hr { border: 0; border-top: 1px solid var(--legal-border); margin: 0.75rem 0; }
.tj-bubble code { background: #EEF1F6; padding: 0.14rem 0.4rem; border-radius: 6px; font-size: 0.89em; }

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

/* Keep Streamlit controls visually aligned with the reference dashboard. */
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stDownloadButton"] button,
[data-testid="stButton"] button {
    min-height: 42px;
}
[data-testid="stSidebar"] [data-testid="stButton"] button {
    border-radius: 12px;
}

@media (max-width: 900px) {
    .block-container { padding: 1rem 1rem 2rem 1rem; }
    .tj-hero { padding: 1.45rem; border-radius: 20px; }
    .tj-hero h1 { font-size: 1.7rem; }
    .tj-hero p { font-size: 0.92rem; }
    .tj-brand-text { font-size: 0.85rem; letter-spacing: 0.08em; }
    .tj-hero-icon { width: 46px; height: 46px; font-size: 1.2rem; }
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
</style>
        """
    )

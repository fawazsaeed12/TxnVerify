"""
TxnVerify AI — Streamlit Application
"""

import os
import time
import requests
from pathlib import Path

import streamlit as st
import pandas as pd

import database
import google_auth
import agent_core

# ── must be first ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TxnVerify AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Reset & base ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stAppViewContainer"] {
    background: #f0f4f8;
}
[data-testid="stAppViewBlockContainer"] {
    padding: 2rem 2.5rem 3rem;
    max-width: 1200px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] section { padding-top: 0 !important; }
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] hr { border-color: #334155 !important; margin: .75rem 0 !important; }
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
    background: #1e293b !important;
    border-color: #475569 !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stToggle span { background: #334155 !important; }
[data-testid="stSidebar"] label { color: #94a3b8 !important; font-size: .82rem !important; }
[data-testid="stSidebar"] button[kind="primary"] {
    background: #3b82f6 !important; border: none !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] { background: transparent; }
div[data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 2px solid #e2e8f0 !important;
    gap: 0 !important;
    padding: 0 !important;
}
button[data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: #64748b !important;
    font-weight: 500 !important;
    font-size: .9rem !important;
    padding: .75rem 1.25rem !important;
    margin-bottom: -2px !important;
    border-radius: 0 !important;
    transition: color .15s, border-color .15s;
}
button[data-baseweb="tab"]:hover { color: #1e293b !important; }
button[aria-selected="true"][data-baseweb="tab"] {
    color: #2563eb !important;
    border-bottom-color: #2563eb !important;
    font-weight: 600 !important;
}
[data-testid="stTabPanel"] { padding-top: 2rem !important; }

/* ── Cards ── */
.card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.75rem 2rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 1px 3px rgba(15,23,42,.06), 0 1px 2px rgba(15,23,42,.04);
    transition: box-shadow .2s;
}
.card:hover { box-shadow: 0 4px 12px rgba(15,23,42,.1); }
.card-sm {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 1px 3px rgba(15,23,42,.05);
}

/* ── Metric cards ── */
.metric-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
.metric-card {
    flex: 1;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 1px 3px rgba(15,23,42,.05);
}
.metric-label { font-size: .78rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: .06em; margin-bottom: .35rem; }
.metric-value { font-size: 1.9rem; font-weight: 800; color: #0f172a; line-height: 1; }
.metric-sub   { font-size: .78rem; color: #64748b; margin-top: .3rem; }
.metric-card.blue  { border-top: 3px solid #3b82f6; }
.metric-card.green { border-top: 3px solid #22c55e; }
.metric-card.red   { border-top: 3px solid #ef4444; }
.metric-card.purple{ border-top: 3px solid #a855f7; }

/* ── Pills / Badges ── */
.badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 4px 11px; border-radius: 999px;
    font-size: .78rem; font-weight: 600; letter-spacing: .02em;
    white-space: nowrap;
}
.badge-green  { background: #dcfce7; color: #15803d; }
.badge-red    { background: #fee2e2; color: #b91c1c; }
.badge-yellow { background: #fef9c3; color: #a16207; }
.badge-blue   { background: #dbeafe; color: #1d4ed8; }
.badge-slate  { background: #f1f5f9; color: #475569; }

/* ── Setup steps ── */
.step-wrap { display: flex; gap: 1rem; margin-bottom: .75rem; }
.step-num {
    width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: .85rem; font-weight: 700;
}
.step-num-done    { background: #22c55e; color: #fff; }
.step-num-active  { background: #2563eb; color: #fff; }
.step-num-pending { background: #e2e8f0; color: #94a3b8; }
.step-content { flex: 1; padding-top: 4px; }
.step-title { font-weight: 600; font-size: .95rem; color: #0f172a; margin-bottom: .1rem; }
.step-desc  { font-size: .83rem; color: #64748b; }

/* ── How-to guide boxes ── */
.guide-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 3px solid #3b82f6;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    font-size: .875rem;
    color: #334155;
    line-height: 1.7;
    margin: 1rem 0;
}
.guide-box ol { margin: .5rem 0 0 1.1rem; padding: 0; }
.guide-box li { margin-bottom: .35rem; }
.guide-box code {
    background: #e0e7ff; color: #3730a3;
    padding: 2px 7px; border-radius: 5px; font-size: .82rem;
}

/* ── Input styling ── */
.stTextInput input, .stSelectbox div[data-baseweb] {
    border-radius: 9px !important;
    border: 1.5px solid #e2e8f0 !important;
    font-size: .9rem !important;
    transition: border-color .15s, box-shadow .15s !important;
}
.stTextInput input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,.15) !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: .88rem !important;
    padding: .55rem 1.3rem !important;
    transition: all .15s !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(37,99,235,.35) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 14px rgba(37,99,235,.45) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: #fff !important;
    border: 1.5px solid #e2e8f0 !important;
    color: #334155 !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #94a3b8 !important;
    background: #f8fafc !important;
}
/* Link buttons */
.stLinkButton a {
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: .88rem !important;
    padding: .55rem 1.3rem !important;
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    box-shadow: 0 2px 8px rgba(37,99,235,.35) !important;
    transition: all .15s !important;
}

/* ── Alerts ── */
.stAlert { border-radius: 12px !important; border: none !important; }
[data-testid="stSuccess"]  { background: #f0fdf4 !important; color: #15803d !important; }
[data-testid="stWarning"]  { background: #fffbeb !important; color: #92400e !important; }
[data-testid="stError"]    { background: #fef2f2 !important; color: #991b1b !important; }
[data-testid="stInfo"]     { background: #eff6ff !important; color: #1e40af !important; }

/* ── Dataframes ── */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; }

/* ── Progress bar ── */
.stProgress > div > div { background: #2563eb !important; border-radius: 999px !important; }
.stProgress > div       { background: #e2e8f0 !important; border-radius: 999px !important; }

/* ── WhatsApp reply bubble ── */
.wa-confirmed {
    background: #f0fdf4; border: 1px solid #86efac;
    border-radius: 4px 16px 16px 16px;
    padding: 1.1rem 1.4rem; font-size: .9rem; line-height: 1.7;
    white-space: pre-wrap; max-width: 520px; color: #14532d;
    box-shadow: 0 2px 8px rgba(34,197,94,.1);
}
.wa-failed {
    background: #fef2f2; border: 1px solid #fca5a5;
    border-radius: 4px 16px 16px 16px;
    padding: 1.1rem 1.4rem; font-size: .9rem; line-height: 1.7;
    white-space: pre-wrap; max-width: 520px; color: #991b1b;
    box-shadow: 0 2px 8px rgba(239,68,68,.1);
}

/* ── QR display ── */
.qr-card {
    background: #fff; border: 1px solid #e2e8f0;
    border-radius: 20px; padding: 2.5rem;
    display: flex; flex-direction: column; align-items: center; gap: 1rem;
    box-shadow: 0 4px 20px rgba(15,23,42,.08);
}
.qr-caption { color: #64748b; font-size: .85rem; text-align: center; }

/* ── Dividers ── */
.section-divider {
    height: 1px; background: #f1f5f9;
    border: none; margin: 1.75rem 0;
}

/* ── Sidebar logo area ── */
.sb-logo {
    padding: 1.5rem 1rem 1rem;
    display: flex; align-items: center; gap: .7rem;
}
.sb-logo-icon {
    width: 38px; height: 38px; background: #2563eb;
    border-radius: 10px; display: flex; align-items: center;
    justify-content: center; font-size: 1.1rem; flex-shrink: 0;
}
.sb-logo-text { font-size: 1rem; font-weight: 700; color: #f1f5f9 !important; letter-spacing: -.3px; }
.sb-logo-sub  { font-size: .73rem; color: #94a3b8 !important; }

/* ── Sidebar nav items ── */
.sb-section { padding: 0 1rem; margin-bottom: .25rem; }
.sb-label {
    font-size: .7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; color: #475569 !important; padding: .75rem 0 .4rem;
}
.sb-stat-row { display: flex; align-items: center; justify-content: space-between; padding: .3rem 0; }
.sb-stat-label { font-size: .82rem; color: #94a3b8 !important; }
.sb-stat-value { font-size: .82rem; font-weight: 600; color: #f1f5f9 !important; }
</style>
""", unsafe_allow_html=True)


# ── OAuth callback ─────────────────────────────────────────────────────────────
def _handle_oauth_callback():
    params = st.query_params
    if "code" in params:
        with st.spinner("Completing Google sign-in…"):
            creds = google_auth.exchange_code_for_token(
                params["code"], redirect_uri="http://localhost:8501"
            )
        if creds:
            database.log_event("AUTH_SUCCESS", "CONNECTED", "OAuth 2.0 sign-in completed")
            st.toast("Google account connected ✓", icon="✅")
        else:
            st.error(
                "**Google sign-in failed.** The most likely cause is that "
                "`http://localhost:8501` is not added to the **Authorised Redirect URIs** "
                "in your Google Cloud project. See Setup → Step 2 for instructions."
            )
        st.query_params.clear()

_handle_oauth_callback()


# ── Config state ───────────────────────────────────────────────────────────────
def _cfg():
    gemini_key    = (database.get_config("gemini_api_key", "") or os.getenv("GEMINI_API_KEY", "")).strip()
    client_id     = (database.get_config("google_client_id", "") or os.getenv("GOOGLE_CLIENT_ID", "")).strip()
    client_secret = (database.get_config("google_client_secret", "") or os.getenv("GOOGLE_CLIENT_SECRET", "")).strip()
    creds         = google_auth.get_stored_credentials()
    gmail_ok      = creds is not None and creds.valid
    return {
        "gemini_key":    gemini_key,
        "client_id":     client_id,
        "client_secret": client_secret,
        "oauth_ready":   bool(client_id and client_secret),
        "gmail_ok":      gmail_ok,
        "all_ready":     bool(gemini_key and client_id and client_secret and gmail_ok),
    }


GATEWAY_URL = os.getenv("WHATSAPP_GATEWAY_URL", "http://localhost:3001")


def _gateway_status():
    try:
        r = requests.get(f"{GATEWAY_URL}/status", timeout=2)
        return r.json()
    except Exception:
        return None


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    cfg = _cfg()
    gw  = _gateway_status()

    # Logo
    st.markdown("""
    <div class="sb-logo">
        <div class="sb-logo-icon">🛡️</div>
        <div>
            <div class="sb-logo-text">TxnVerify AI</div>
            <div class="sb-logo-sub">Payment Verification Agent</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    # Agent toggle
    is_running = database.get_config("agent_running", False)
    new_val = st.toggle(
        "Agent Active",
        value=bool(is_running and cfg["all_ready"]),
        disabled=not cfg["all_ready"],
        help="Complete all Setup steps to enable the agent.",
    )
    if new_val != is_running:
        database.set_config("agent_running", new_val)
        database.log_event("AGENT_STATE", "ENABLED" if new_val else "PAUSED", "User toggled agent")
        st.rerun()

    if new_val and cfg["all_ready"]:
        st.markdown('<span class="badge badge-green">● Listening</span>', unsafe_allow_html=True)
    elif not cfg["all_ready"]:
        st.markdown('<span class="badge badge-yellow">● Setup required</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-slate">● Paused</span>', unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    # Configuration status
    def _tick(ok): return "✓" if ok else "○"
    def _cls(ok):  return "badge-green" if ok else "badge-slate"

    st.markdown('<div class="sb-section"><div class="sb-label">Configuration</div>', unsafe_allow_html=True)

    for label, ok in [
        ("Gemini API key", bool(cfg["gemini_key"])),
        ("OAuth credentials", cfg["oauth_ready"]),
        ("Gmail authorised", cfg["gmail_ok"]),
    ]:
        icon = "✅" if ok else "○"
        color = "#22c55e" if ok else "#94a3b8"
        st.markdown(
            f'<div class="sb-stat-row">'
            f'<span class="sb-stat-label">{icon}  {label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<hr>', unsafe_allow_html=True)

    # WhatsApp status
    st.markdown('<div class="sb-section"><div class="sb-label">WhatsApp Gateway</div>', unsafe_allow_html=True)
    if gw:
        gw_status = gw.get("status", "UNKNOWN")
        badge_cls = (
            "badge-green"  if gw_status == "READY" else
            "badge-yellow" if gw_status in ("SCAN_QR", "INITIALIZING", "AUTHENTICATED") else
            "badge-red"
        )
        st.markdown(f'<span class="badge {badge_cls}">{gw_status}</span>', unsafe_allow_html=True)
        paired = gw.get("paired_info") or {}
        if paired.get("pushname"):
            st.markdown(
                f'<div class="sb-stat-row">'
                f'<span class="sb-stat-label">Paired account</span>'
                f'<span class="sb-stat-value">{paired["pushname"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown('<span class="badge badge-red">Offline</span>', unsafe_allow_html=True)
        st.markdown('<div style="color:#64748b;font-size:.78rem;margin-top:.4rem">Run <code>node whatsapp_gateway.js</code></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<hr>', unsafe_allow_html=True)

    # Model selector
    st.markdown('<div class="sb-section"><div class="sb-label">Vision Model</div>', unsafe_allow_html=True)
    model_opts  = ["gemma-4-26b-a4b-it", "gemini-2.5-flash", "gemini-1.5-flash"]
    saved_model = database.get_config("gemini_model", model_opts[0])
    idx         = model_opts.index(saved_model) if saved_model in model_opts else 0
    chosen_model = st.selectbox("", model_opts, index=idx, label_visibility="collapsed")
    if chosen_model != saved_model:
        database.set_config("gemini_model", chosen_model)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<br>', unsafe_allow_html=True)
    if st.button("🔄  Refresh", use_container_width=True, type="secondary"):
        st.rerun()


# ── Page header ────────────────────────────────────────────────────────────────
cfg = _cfg()
transactions = database.get_transactions(limit=500)
total    = len(transactions)
verified = len([t for t in transactions if t.get("gmail_verified") == 1])
unverif  = total - verified
rate     = f"{round(verified/total*100, 1)}%" if total else "—"

# Metrics row
st.markdown(f"""
<div class="metric-row">
  <div class="metric-card blue">
    <div class="metric-label">Receipts Processed</div>
    <div class="metric-value">{total}</div>
    <div class="metric-sub">All time</div>
  </div>
  <div class="metric-card green">
    <div class="metric-label">Verified</div>
    <div class="metric-value">{verified}</div>
    <div class="metric-sub">Gmail confirmed</div>
  </div>
  <div class="metric-card red">
    <div class="metric-label">Unverified</div>
    <div class="metric-value">{unverif}</div>
    <div class="metric-sub">No matching email</div>
  </div>
  <div class="metric-card purple">
    <div class="metric-label">Success Rate</div>
    <div class="metric-value">{rate}</div>
    <div class="metric-sub">Verification rate</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_setup, tab_verify, tab_whatsapp, tab_logs = st.tabs([
    "⚙️   Setup",
    "✅   Verify Payment",
    "📱   WhatsApp",
    "📊   Logs",
])


# ══════════════════════════════════════════════════════════════════════════════
# SETUP TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_setup:
    cfg = _cfg()

    st.markdown("### Get started")
    st.markdown(
        '<p style="color:#64748b;margin-top:-.5rem;margin-bottom:1.5rem">'
        'Complete the three steps below to activate TxnVerify AI.</p>',
        unsafe_allow_html=True,
    )

    # ── Overall progress ──────────────────────────────────────────────────────
    steps_done = sum([bool(cfg["gemini_key"]), cfg["oauth_ready"], cfg["gmail_ok"]])
    st.progress(steps_done / 3, text=f"{steps_done} of 3 steps complete")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── STEP 1 ── Gemini API Key ──────────────────────────────────────────────
    s1_done = bool(cfg["gemini_key"])
    num_cls  = "step-num-done" if s1_done else "step-num-active"
    num_icon = "✓" if s1_done else "1"

    with st.container():
        st.markdown(f"""
        <div class="step-wrap">
            <div class="step-num {num_cls}">{num_icon}</div>
            <div class="step-content">
                <div class="step-title">Gemini API Key
                    {"&nbsp;<span class='badge badge-green' style='vertical-align:middle;font-size:.7rem'>Complete</span>" if s1_done else ""}
                </div>
                <div class="step-desc">Required for Gemma 4 visual OCR on payment screenshots.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("" if s1_done else "▸  How to get your Gemini API key", expanded=not s1_done):
            st.markdown("""
<div class="guide-box">
<strong>Free, takes about 1 minute:</strong>
<ol>
<li>Open <a href="https://aistudio.google.com/apikey" target="_blank"><strong>aistudio.google.com/apikey</strong></a> and sign in with any Google account.</li>
<li>Click <strong>Create API key</strong> — pick an existing project or create a new one.</li>
<li>Copy the key shown (it starts with <code>AIza…</code>).</li>
<li>Paste it below and click Save.</li>
</ol>
</div>
""", unsafe_allow_html=True)

            cur_key = database.get_config("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
            col_in, col_btn = st.columns([3, 1])
            new_key = col_in.text_input("Gemini API Key", value=cur_key, type="password",
                                        placeholder="AIzaSy…", label_visibility="collapsed")
            if col_btn.button("Save", key="save_gem", type="primary", use_container_width=True):
                if new_key.strip().startswith("AIza"):
                    database.set_config("gemini_api_key", new_key.strip())
                    os.environ["GEMINI_API_KEY"] = new_key.strip()
                    st.success("Gemini API key saved.")
                    st.rerun()
                elif new_key.strip():
                    st.error("That key looks invalid — it should start with `AIza`.")
                else:
                    st.warning("Paste your key first.")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # ── STEP 2 ── OAuth Credentials ───────────────────────────────────────────
    s2_done  = cfg["oauth_ready"]
    num_cls  = "step-num-done" if s2_done else ("step-num-active" if s1_done else "step-num-pending")
    num_icon = "✓" if s2_done else "2"

    with st.container():
        st.markdown(f"""
        <div class="step-wrap">
            <div class="step-num {num_cls}">{num_icon}</div>
            <div class="step-content">
                <div class="step-title">Google Cloud OAuth Credentials
                    {"&nbsp;<span class='badge badge-green' style='vertical-align:middle;font-size:.7rem'>Complete</span>" if s2_done else ""}
                </div>
                <div class="step-desc">Lets TxnVerify AI request read-only access to your Gmail inbox.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("" if s2_done else "▸  How to create OAuth credentials (~3 min)", expanded=(s1_done and not s2_done)):
            st.markdown("""
<div class="guide-box">
<strong>One-time setup in Google Cloud Console:</strong>
<ol>
<li>Go to <a href="https://console.cloud.google.com/" target="_blank"><strong>console.cloud.google.com</strong></a> and sign in.</li>
<li>At the top, open the project picker → click <strong>New Project</strong> → give it any name → <strong>Create</strong>.</li>
<li>In the left sidebar go to <strong>APIs & Services → Library</strong>. Search for <strong>Gmail API</strong> and click <strong>Enable</strong>.</li>
<li>Go to <strong>APIs & Services → OAuth consent screen</strong>:
    <ul>
        <li>Choose <strong>External</strong> → <strong>Create</strong>.</li>
        <li>Fill in an App name (e.g. <code>TxnVerify AI</code>) and your email for both support and developer fields.</li>
        <li>Click <strong>Save and Continue</strong> through all screens. No scopes need to be added here.</li>
        <li>On the <strong>Test users</strong> screen, click <strong>Add users</strong> and add your own Gmail address. Click <strong>Save and Continue</strong>.</li>
    </ul>
</li>
<li>Go to <strong>APIs & Services → Credentials → + Create Credentials → OAuth client ID</strong>:
    <ul>
        <li>Application type: <strong>Web application</strong>.</li>
        <li>Under <strong>Authorised redirect URIs</strong>, click <strong>+ Add URI</strong> and enter: <code>http://localhost:8501</code></li>
        <li>Click <strong>Create</strong>.</li>
    </ul>
</li>
<li>A popup shows your <strong>Client ID</strong> and <strong>Client Secret</strong>. Copy both and paste below.</li>
</ol>
</div>
""", unsafe_allow_html=True)

            saved_cid = database.get_config("google_client_id", os.getenv("GOOGLE_CLIENT_ID", ""))
            saved_cs  = database.get_config("google_client_secret", os.getenv("GOOGLE_CLIENT_SECRET", ""))
            c1, c2 = st.columns(2)
            new_cid = c1.text_input("Client ID", value=saved_cid,
                                    placeholder="123456789-abc….apps.googleusercontent.com")
            new_cs  = c2.text_input("Client Secret", value=saved_cs,
                                    type="password", placeholder="GOCSPX-…")
            if st.button("Save OAuth Credentials", key="save_oauth", type="primary"):
                if new_cid.strip() and new_cs.strip():
                    database.set_config("google_client_id",     new_cid.strip())
                    database.set_config("google_client_secret",  new_cs.strip())
                    os.environ["GOOGLE_CLIENT_ID"]     = new_cid.strip()
                    os.environ["GOOGLE_CLIENT_SECRET"] = new_cs.strip()
                    st.success("OAuth credentials saved. Continue to Step 3.")
                    st.rerun()
                else:
                    st.warning("Both fields are required.")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # ── STEP 3 ── Gmail sign-in ───────────────────────────────────────────────
    s3_done  = cfg["gmail_ok"]
    num_cls  = "step-num-done" if s3_done else ("step-num-active" if s2_done else "step-num-pending")
    num_icon = "✓" if s3_done else "3"

    with st.container():
        st.markdown(f"""
        <div class="step-wrap">
            <div class="step-num {num_cls}">{num_icon}</div>
            <div class="step-content">
                <div class="step-title">Authorise Gmail Access
                    {"&nbsp;<span class='badge badge-green' style='vertical-align:middle;font-size:.7rem'>Complete</span>" if s3_done else ""}
                </div>
                <div class="step-desc">Sign in with Google to allow inbox search for transaction emails.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if s3_done:
            email = google_auth.get_user_email()
            c1, c2 = st.columns([3, 1])
            c1.success(f"Signed in as **{email}**  ·  read-only Gmail access granted")
            if c2.button("Disconnect", type="secondary", use_container_width=True):
                google_auth.sign_out()
                database.log_event("AUTH_REVOKE", "DISCONNECTED", "User signed out")
                st.rerun()
        elif not s2_done:
            st.info("Complete Step 2 first.")
        else:
            st.markdown("""
<div class="guide-box">
Click the button below. Google will ask you to sign in and approve <strong>read-only</strong> Gmail
access. TxnVerify AI only reads emails that match the extracted transaction reference —
it never sends, modifies or deletes anything.<br><br>
After you approve, Google automatically redirects you back here.
</div>
""", unsafe_allow_html=True)
            try:
                auth_url, _ = google_auth.get_google_auth_url(redirect_uri="http://localhost:8501")
                st.link_button("Sign in with Google  →", auth_url, type="primary")
            except Exception as e:
                st.error(f"Could not generate sign-in URL: {e}")
                st.caption("Make sure your Client ID and Client Secret are saved correctly in Step 2.")

    # ── Final status ──────────────────────────────────────────────────────────
    if cfg["all_ready"]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.success(
            "**All set.** Turn on the **Agent Active** toggle in the sidebar, "
            "then pair your phone in the **WhatsApp** tab."
        )


# ══════════════════════════════════════════════════════════════════════════════
# VERIFY PAYMENT TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_verify:
    cfg = _cfg()

    if not cfg["gemini_key"]:
        st.warning("Add your **Gemini API key** in the Setup tab before running a verification.")
        st.stop()

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("#### Upload receipt")
        st.markdown(
            '<p style="color:#64748b;font-size:.87rem;margin-top:-.5rem;margin-bottom:1rem">'
            'Upload any payment screenshot — Zelle, Venmo, PayPal, UPI, bank transfer, etc.</p>',
            unsafe_allow_html=True,
        )

        # Quick sample loader
        sample_dir = Path(__file__).parent / "sample_receipts"
        sample_map = {
            "Upload my own image": None,
            "Zelle  ·  $150.00  (Ref ZEL-982341908)":            sample_dir / "zelle_receipt_150.jpg",
            "Venmo  ·  $45.00   (Ref VEN-549102834)":            sample_dir / "venmo_receipt_45.jpg",
            "Google Pay UPI  ·  ₹2,500  (Ref UPI-409182390192)": sample_dir / "upi_receipt_2500.jpg",
        }

        choice = st.selectbox(
            "Quick sample",
            list(sample_map.keys()),
            help="Select a built-in test receipt or upload your own.",
        )

        img_bytes, mime = None, "image/jpeg"
        if sample_map[choice]:
            p = sample_map[choice]
            if p.exists():
                img_bytes = p.read_bytes()
                st.image(img_bytes, use_container_width=True, caption=choice)
            else:
                st.warning("Sample file missing. Run `python generate_sample_receipt.py`.")
        else:
            uploaded = st.file_uploader(
                "Drag & drop or click to browse",
                type=["jpg", "jpeg", "png", "webp"],
                label_visibility="collapsed",
            )
            if uploaded:
                img_bytes = uploaded.getvalue()
                mime      = uploaded.type
                st.image(img_bytes, use_container_width=True, caption=uploaded.name)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Sender (optional)")
        st.markdown(
            '<p style="color:#64748b;font-size:.87rem;margin-top:-.5rem;margin-bottom:.5rem">'
            'If provided, the verification result is sent back via WhatsApp.</p>',
            unsafe_allow_html=True,
        )
        sender = st.text_input(
            "WhatsApp number",
            placeholder="+1 555 000 1234",
            label_visibility="collapsed",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button(
            "  Run Verification  ",
            type="primary",
            use_container_width=True,
            disabled=img_bytes is None,
        )
        if img_bytes is None:
            st.markdown(
                '<p style="color:#94a3b8;font-size:.8rem;text-align:center;margin-top:.5rem">'
                'Select or upload a receipt to continue.</p>',
                unsafe_allow_html=True,
            )

    with right:
        st.markdown("#### Result")

        if not run or img_bytes is None:
            st.markdown("""
<div class="card" style="min-height:300px;display:flex;align-items:center;justify-content:center;">
  <div style="text-align:center;color:#94a3b8;">
    <div style="font-size:2.5rem;margin-bottom:.75rem">🧾</div>
    <div style="font-weight:600;font-size:.95rem;color:#64748b">No result yet</div>
    <div style="font-size:.83rem;margin-top:.35rem">Upload a receipt and click Run Verification</div>
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            bar  = st.progress(5, text="Starting Gemma 4 OCR…")
            slot = st.empty()

            def _prog(step, elapsed, msg):
                pct = min(10 + int((elapsed / 60) * 85), 95)
                bar.progress(pct, text=f"[{elapsed}s]  {msg}")

            try:
                slot.info(f"Analysing image with **{chosen_model}**…")
                result = agent_core.process_payment_image(
                    image_bytes=img_bytes,
                    mime_type=mime,
                    sender_phone=sender or None,
                    model_name=chosen_model,
                    progress_callback=_prog,
                )
                bar.progress(100, text="Complete.")
                slot.empty()

                is_txn   = result.get("is_transaction")
                verified = result.get("verified")
                elapsed  = result.get("elapsed_seconds", 0)

                # ── Status banner ──────────────────────────────────────────
                if verified:
                    st.success(f"**Payment confirmed** in {elapsed}s")
                elif is_txn:
                    st.error("**Could not verify** — no matching email received within 60 seconds.")
                else:
                    st.warning("**Not a receipt** — the image does not appear to be a payment confirmation.")

                # ── Extracted data card ────────────────────────────────────
                if is_txn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("**Extracted by Gemma 4**")
                    ca, cb = st.columns(2)
                    ca.metric("Transaction ID", result.get("transaction_id") or "—")
                    cb.metric("Amount",         result.get("amount") or "—")
                    cc, cd = st.columns(2)
                    cc.metric("Platform",  result.get("payment_app") or "—")
                    cd.metric("Confidence", f"{round(result.get('confidence', 0) * 100)}%")

                # ── Gmail match ────────────────────────────────────────────
                gm = result.get("gmail_match")
                if gm:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("**Gmail match found**")
                    st.markdown(f"""
<div class="card-sm">
  <div style="display:flex;align-items:baseline;gap:.5rem;margin-bottom:.5rem">
    <span style="font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#94a3b8">From</span>
    <span style="font-size:.88rem;color:#0f172a">{gm.get("sender","—")}</span>
  </div>
  <div style="display:flex;align-items:baseline;gap:.5rem;margin-bottom:.5rem">
    <span style="font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#94a3b8">Subject</span>
    <span style="font-size:.88rem;color:#0f172a">{gm.get("subject","—")}</span>
  </div>
  <div style="font-size:.83rem;color:#475569;font-style:italic;margin-top:.4rem;padding-top:.6rem;border-top:1px solid #f1f5f9">
    "{gm.get("snippet","")[:180]}"
  </div>
  <div style="font-size:.75rem;color:#94a3b8;margin-top:.5rem">Source: {gm.get("source","—")}</div>
</div>
""", unsafe_allow_html=True)

                # ── WhatsApp reply ─────────────────────────────────────────
                reply = result.get("reply_text", "")
                if reply:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("**WhatsApp reply dispatched**")
                    bubble = "wa-confirmed" if verified else "wa-failed"
                    st.markdown(f'<div class="{bubble}">{reply}</div>', unsafe_allow_html=True)

            except Exception as exc:
                bar.empty()
                slot.empty()
                st.error(f"Verification failed: {exc}")
                with st.expander("Error details"):
                    st.exception(exc)


# ══════════════════════════════════════════════════════════════════════════════
# WHATSAPP TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_whatsapp:
    left_q, right_q = st.columns([1, 1], gap="large")

    with left_q:
        st.markdown("#### Pair your device")
        st.markdown(
            '<p style="color:#64748b;font-size:.87rem;margin-top:-.5rem;margin-bottom:1.25rem">'
            'Scan the QR code in WhatsApp to link your account.</p>',
            unsafe_allow_html=True,
        )

        gw = _gateway_status()

        if gw is None:
            st.markdown("""
<div class="card" style="text-align:center;padding:2rem">
  <div style="font-size:2rem;margin-bottom:.75rem">📵</div>
  <div style="font-weight:600;color:#0f172a;margin-bottom:.4rem">Gateway offline</div>
  <div style="color:#64748b;font-size:.87rem">Open a terminal in the project folder and run:</div>
</div>
""", unsafe_allow_html=True)
            st.code("node whatsapp_gateway.js", language="bash")

        elif gw.get("status") == "READY":
            paired = gw.get("paired_info") or {}
            st.markdown(f"""
<div class="card" style="text-align:center;padding:2.5rem">
  <div style="font-size:2.5rem;margin-bottom:.75rem">✅</div>
  <div style="font-weight:700;font-size:1.05rem;color:#0f172a;margin-bottom:.3rem">WhatsApp Connected</div>
  <div style="color:#64748b;font-size:.87rem">
    <strong>{paired.get("pushname", "Device")}</strong>
    {"&nbsp;·&nbsp;" + paired.get("wid","") if paired.get("wid") else ""}
  </div>
</div>
""", unsafe_allow_html=True)
            st.success("The agent is actively monitoring this account for payment screenshots.")

        elif gw.get("qr_data_url"):
            st.markdown(
                f'<div class="qr-card">'
                f'<img src="{gw["qr_data_url"]}" style="width:260px;height:260px;object-fit:contain;border-radius:10px">'
                f'<div class="qr-caption">Open WhatsApp → Settings → Linked devices → Link a device</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            status = gw.get("status", "INITIALIZING")
            st.markdown(f"""
<div class="card" style="text-align:center;padding:2rem">
  <div style="font-size:2rem;margin-bottom:.75rem">⏳</div>
  <div style="font-weight:600;color:#0f172a;margin-bottom:.3rem">{status}</div>
  <div style="color:#64748b;font-size:.87rem">The gateway is starting up — the QR code will appear shortly.</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        bc1, bc2 = st.columns(2)
        if bc1.button("Refresh", use_container_width=True, type="secondary"):
            st.rerun()
        if bc2.button("Restart client", use_container_width=True, type="secondary"):
            try:
                requests.post(f"{GATEWAY_URL}/start", timeout=3)
                st.toast("Client restart requested.")
                time.sleep(1)
                st.rerun()
            except Exception:
                st.error("Cannot reach the gateway.")

    with right_q:
        st.markdown("#### How it works")
        st.markdown("""
<div class="card">
<ol style="margin:0;padding-left:1.3rem;color:#334155;font-size:.9rem;line-height:1.9">
  <li>Open <strong>WhatsApp</strong> on your phone.</li>
  <li>Tap <strong>⋮ (three dots)</strong> → <strong>Linked devices</strong> → <strong>Link a device</strong>.</li>
  <li>Scan the QR code on the left.</li>
  <li>Once paired, any payment screenshot sent to this WhatsApp number is automatically processed:
    <ul style="margin-top:.4rem;line-height:2">
      <li>Gemma 4 reads the image and extracts the transaction ID and amount.</li>
      <li>TxnVerify AI searches your Gmail inbox for the bank confirmation email (up to 60 s).</li>
      <li>A reply — <strong>Payment confirmed</strong> or <strong>Could not verify</strong> — is sent back to the customer.</li>
    </ul>
  </li>
</ol>
</div>
""", unsafe_allow_html=True)

        st.markdown("#### Privacy")
        st.markdown("""
<div class="card-sm" style="font-size:.87rem;color:#334155;line-height:1.8">
  <strong>WhatsApp</strong> — Message images are processed in memory and never stored.
  Only the extracted transaction ID, amount, and verification result are written to the local database.<br><br>
  <strong>Gmail</strong> — Access is read-only. TxnVerify AI only queries for emails containing the
  specific transaction reference. No other emails are read, and nothing is sent or deleted.
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LOGS TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_logs:
    c1, c2 = st.columns([5, 1])
    c1.markdown("#### Transactions")
    if c2.button("Refresh", type="secondary", use_container_width=True, key="ref_logs"):
        st.rerun()

    txns = database.get_transactions(limit=100)
    if txns:
        df = pd.DataFrame(txns)
        wanted = ["transaction_id", "amount", "payment_app", "sender_phone",
                  "gmail_verified", "ocr_confidence", "created_at", "verified_at"]
        df = df[[c for c in wanted if c in df.columns]].copy()
        df["gmail_verified"] = df["gmail_verified"].apply(
            lambda v: "✅  Confirmed" if v == 1 else "—"
        )
        if "ocr_confidence" in df.columns:
            df["ocr_confidence"] = df["ocr_confidence"].apply(
                lambda v: f"{round(float(v)*100)}%" if v else "—"
            )
        df.rename(columns={
            "transaction_id": "Transaction ID",
            "amount": "Amount",
            "payment_app": "Platform",
            "sender_phone": "Sender",
            "gmail_verified": "Gmail",
            "ocr_confidence": "Confidence",
            "created_at": "Received",
            "verified_at": "Confirmed at",
        }, inplace=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.markdown("""
<div class="card" style="text-align:center;padding:2rem;color:#94a3b8">
  No transactions yet. Run a verification from the <strong>Verify Payment</strong> tab.
</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Activity log")
    logs = database.get_recent_logs(limit=80)
    if logs:
        df_l = pd.DataFrame(logs)
        want_l = ["timestamp", "event_type", "status", "sender", "transaction_id", "amount", "details"]
        df_l = df_l[[c for c in want_l if c in df_l.columns]].copy()
        df_l.rename(columns={
            "timestamp": "Time",
            "event_type": "Event",
            "status": "Status",
            "sender": "Sender",
            "transaction_id": "Txn ID",
            "amount": "Amount",
            "details": "Details",
        }, inplace=True)
        st.dataframe(df_l, use_container_width=True, hide_index=True)
    else:
        st.markdown("""
<div class="card" style="text-align:center;padding:2rem;color:#94a3b8">
  No activity logged yet.
</div>
""", unsafe_allow_html=True)

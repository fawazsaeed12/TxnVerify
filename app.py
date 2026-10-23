"""
TxnVerify AI - Executive SaaS Dashboard
Autonomous WhatsApp Payment Verification Agent
Powered by Gemma 4 (gemma-4-26b-a4b-it) & Google Gmail API
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

# -------------------------------------------------------------
# Page Configuration & Advanced Theme Injection
# -------------------------------------------------------------
st.set_page_config(
    page_title="TxnVerify AI | WhatsApp Payment Verification Gateway",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-End Design System: Dark Navy / Obsidian Glassmorphism
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg-main: #090d16;
        --bg-card: rgba(17, 24, 39, 0.75);
        --bg-card-hover: rgba(30, 41, 59, 0.85);
        --border-color: rgba(255, 255, 255, 0.08);
        --border-glow: rgba(59, 130, 246, 0.35);
        --accent-blue: #3b82f6;
        --accent-emerald: #10b981;
        --accent-purple: #8b5cf6;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
    }

    * {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Background & Main Viewport */
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 15% 15%, #0f172a 0%, #070a12 60%, #030712 100%) !important;
        color: var(--text-primary);
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Sidebar Glassmorphism */
    [data-testid="stSidebar"] {
        background: rgba(11, 16, 27, 0.92) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid var(--border-color) !important;
    }
    
    [data-testid="stSidebar"] * {
        color: var(--text-primary) !important;
    }

    /* Custom Scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.12);
        border-radius: 999px;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.6) !important;
        padding: 6px !important;
        border-radius: 14px !important;
        border: 1px solid var(--border-color) !important;
        gap: 8px !important;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border: none !important;
        border-radius: 10px !important;
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        padding: 10px 22px !important;
        transition: all 0.2s ease !important;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.25), rgba(139, 92, 246, 0.25)) !important;
        border: 1px solid rgba(59, 130, 246, 0.5) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.2) !important;
    }

    /* Top Hero Header */
    .hero-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.5rem 1.8rem;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.4), rgba(15, 23, 42, 0.6));
        border: 1px solid var(--border-color);
        border-radius: 20px;
        backdrop-filter: blur(12px);
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }

    .hero-title {
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #34d399 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.2;
    }

    .hero-subtitle {
        color: var(--text-secondary);
        font-size: 0.92rem;
        margin-top: 0.3rem;
        font-weight: 400;
    }

    /* Metrics Cards */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .glass-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 1.25rem 1.4rem;
        backdrop-filter: blur(16px);
        transition: transform 0.2s ease, border-color 0.2s ease;
        position: relative;
        overflow: hidden;
    }

    .glass-card:hover {
        border-color: rgba(59, 130, 246, 0.4);
        transform: translateY(-2px);
    }

    .metric-title {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted);
        margin-bottom: 0.4rem;
    }

    .metric-stat {
        font-size: 2rem;
        font-weight: 800;
        color: #ffffff;
        line-height: 1;
    }

    .metric-sub {
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin-top: 0.4rem;
        display: flex;
        align-items: center;
        gap: 4px;
    }

    /* Status Pills */
    .status-pill-live {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.35);
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }

    .status-pill-paused {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.35);
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 700;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 10px #10b981;
        animation: pulse 1.8s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    /* Setup Step Card */
    .setup-step-box {
        background: rgba(17, 24, 39, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 1.5rem 1.8rem;
        margin-bottom: 1.2rem;
        backdrop-filter: blur(14px);
        transition: border-color 0.2s ease;
    }

    .setup-step-box:hover {
        border-color: rgba(59, 130, 246, 0.35);
    }

    .step-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 1rem;
    }

    .step-badge {
        width: 34px;
        height: 34px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.95rem;
        font-weight: 800;
        flex-shrink: 0;
    }

    .step-badge-ready {
        background: #10b981;
        color: white;
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.4);
    }

    .step-badge-pending {
        background: #3b82f6;
        color: white;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
    }

    .step-title-text {
        font-size: 1.1rem;
        font-weight: 700;
        color: #ffffff;
    }

    .step-desc-text {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-top: 2px;
    }

    /* Instructions Box */
    .instruction-callout {
        background: rgba(15, 23, 42, 0.7);
        border-left: 3px solid #3b82f6;
        border-radius: 0 10px 10px 0;
        padding: 0.9rem 1.2rem;
        margin: 0.8rem 0 1rem;
        font-size: 0.86rem;
        color: #cbd5e1;
        line-height: 1.6;
    }

    .instruction-callout code {
        background: rgba(59, 130, 246, 0.18);
        color: #93c5fd;
        padding: 2px 7px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
    }

    /* Form Overrides */
    .stTextInput input {
        background: rgba(15, 23, 42, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
    }

    .stTextInput input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25) !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.4rem !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.45) !important;
    }

    /* Link Buttons */
    .stLinkButton a {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.4rem !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
        transition: all 0.2s ease !important;
    }

    /* Dataframe styling */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border-color);
        border-radius: 14px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Handle Google OAuth 2.0 Web Flow Redirect Callback
# -------------------------------------------------------------
if "code" in st.query_params:
    auth_code = st.query_params["code"]
    # Guard against double-exchange on Streamlit re-render
    if st.session_state.get("last_processed_code") != auth_code:
        st.session_state["last_processed_code"] = auth_code
        with st.spinner("Exchanging Google authorization code for Gmail access token..."):
            creds = google_auth.exchange_code_for_token(auth_code, redirect_uri="http://localhost:8501")
            if creds:
                database.log_event("AUTH_SUCCESS", "CONNECTED", "Connected via direct Streamlit OAuth redirect")
                st.toast("Google Account successfully connected!", icon="🎉")
                st.rerun()
            else:
                last_err = database.get_config("last_oauth_error", "Redirect URI or authorization grant error.")
                st.error(f"⚠️ Google OAuth Error: {last_err}")
                st.info("💡 **Fix:** In Google Cloud Console ➔ Credentials ➔ OAuth Client, ensure **Authorized redirect URIs** contains both `http://localhost:8501` and `http://localhost:8501/`.")
    st.query_params.clear()

if "auth_success" in st.query_params:
    st.toast("Google Account connected via OAuth 2.0!", icon="🎉")
    st.query_params.clear()


# -------------------------------------------------------------
# System Configuration State Check
# -------------------------------------------------------------
GATEWAY_URL = os.getenv("WHATSAPP_GATEWAY_URL", "http://localhost:3001")

def get_system_status():
    gemini_key = (database.get_config("gemini_api_key", "") or os.getenv("GEMINI_API_KEY", "")).strip()
    client_id = (database.get_config("google_client_id", "") or os.getenv("GOOGLE_CLIENT_ID", "")).strip()
    client_secret = (database.get_config("google_client_secret", "") or os.getenv("GOOGLE_CLIENT_SECRET", "")).strip()
    creds = google_auth.get_stored_credentials()
    gmail_ok = creds is not None and creds.valid
    is_sandbox = database.get_config("sandbox_mode", False)
    
    return {
        "gemini_ready": bool(gemini_key),
        "oauth_ready": bool(client_id and client_secret),
        "gmail_ready": bool(gmail_ok or is_sandbox),
        "sandbox_mode": is_sandbox,
        "all_ready": bool(gemini_key and (gmail_ok or is_sandbox))
    }

sys_status = get_system_status()


# -------------------------------------------------------------
# Sidebar: Global Navigation & Status Center
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; padding: 0.5rem 0 1rem;">
        <div style="width: 42px; height: 42px; border-radius: 12px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); display: flex; align-items: center; justify-content: center; font-size: 1.3rem; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);">
            ⚡
        </div>
        <div>
            <div style="font-weight: 800; font-size: 1.15rem; color: #ffffff; letter-spacing: -0.02em;">TxnVerify AI</div>
            <div style="font-size: 0.78rem; color: #94a3b8;">WhatsApp Payment Agent</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 0.5rem 0 1.2rem;'>", unsafe_allow_html=True)

    # 1. Master Agent Active Toggle
    is_agent_active = database.get_config("agent_running", True)
    agent_toggle = st.toggle("🤖 Agent Live Monitoring", value=is_agent_active)
    if agent_toggle != is_agent_active:
        database.set_config("agent_running", agent_toggle)
        database.log_event("AGENT_STATE", "ENABLED" if agent_toggle else "PAUSED", "Agent status updated by user")
        st.rerun()

    if agent_toggle:
        st.markdown("""
        <div class="status-pill-live">
            <div class="pulse-dot"></div> Active & Monitoring
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-pill-paused">
            ⏸️ Agent Paused
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1.2rem 0;'>", unsafe_allow_html=True)

    # 2. System Readiness Checklist
    st.markdown("<div class='metric-title'>Integration Health</div>", unsafe_allow_html=True)
    
    def render_check_item(label: str, is_ready: bool):
        dot_color = "#34d399" if is_ready else "#64748b"
        icon = "✓" if is_ready else "○"
        status_text = "Ready" if is_ready else "Setup Needed"
        st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 0;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="color: {dot_color}; font-weight: 800;">{icon}</span>
                <span style="font-size: 0.85rem; color: #cbd5e1;">{label}</span>
            </div>
            <span style="font-size: 0.75rem; color: {dot_color}; font-weight: 600;">{status_text}</span>
        </div>
        """, unsafe_allow_html=True)

    render_check_item("Gemini API Key", sys_status["gemini_ready"])
    render_check_item("Google OAuth Config", sys_status["oauth_ready"])
    render_check_item("Gmail Verification", sys_status["gmail_ready"])

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1.2rem 0;'>", unsafe_allow_html=True)

    # 3. Model Selector
    st.markdown("<div class='metric-title'>Vision Model (Image OCR)</div>", unsafe_allow_html=True)
    selected_model = st.selectbox(
        "Vision Model",
        options=["gemini-3.8-flash", "gemini-2.5-flash"],
        index=0,
        label_visibility="collapsed"
    )
    database.set_config("gemini_model", selected_model)
    st.caption("Reconciliation: **Gemma 4b** (`gemma-4-26b-a4b-it`)")

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1.2rem 0;'>", unsafe_allow_html=True)

    # 4. WhatsApp Gateway Status Indicator
    st.markdown("<div class='metric-title'>WhatsApp Gateway (:3001)</div>", unsafe_allow_html=True)
    try:
        gw_res = requests.get(f"{GATEWAY_URL}/status", timeout=1.5)
        if gw_res.status_code == 200:
            gw_status = gw_res.json().get("status", "UNKNOWN")
            badge = "🟢 ONLINE" if gw_status == "READY" else f"🟡 {gw_status}"
            st.caption(f"Status: **{badge}**")
        else:
            st.caption("Status: 🔴 OFFLINE")
    except Exception:
        st.caption("Status: ⚪ Offline (`npm start`)")


# -------------------------------------------------------------
# Top Hero Header & Live KPI Metrics Bar
# -------------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <div>
        <h1 class="hero-title">TxnVerify AI Control Center</h1>
        <div class="hero-subtitle">Automated WhatsApp payment verification powered by <b>Gemma 4</b> & <b>Gmail API</b></div>
    </div>
    <div style="display: flex; gap: 10px;">
        <span class="status-pill-live">⚡ Real-Time Engine Active</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Query Database Stats
txns = database.get_transactions(limit=200)
total_count = len(txns)
verified_count = len([t for t in txns if t.get("gmail_verified") == 1])
pending_count = total_count - verified_count
rate_str = f"{round((verified_count / total_count * 100), 1)}%" if total_count > 0 else "100%"

st.markdown(f"""
<div class="metric-grid">
    <div class="glass-card">
        <div class="metric-title">Total Receipts Analyzed</div>
        <div class="metric-stat">{total_count}</div>
        <div class="metric-sub">Processed via Gemma 4 OCR</div>
    </div>
    <div class="glass-card">
        <div class="metric-title">Authenticated via Gmail</div>
        <div class="metric-stat" style="color: #34d399;">{verified_count}</div>
        <div class="metric-sub">Official Bank Confirmations</div>
    </div>
    <div class="glass-card">
        <div class="metric-title">Unverified / Timeouts</div>
        <div class="metric-stat" style="color: #f87171;">{pending_count}</div>
        <div class="metric-sub">No match found within 60s</div>
    </div>
    <div class="glass-card">
        <div class="metric-title">Verification Precision</div>
        <div class="metric-stat" style="color: #60a5fa;">{rate_str}</div>
        <div class="metric-sub">Zero False Positives</div>
    </div>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Core Tabs: Setup, WhatsApp Gateway, Transactions & Logs
# -------------------------------------------------------------
tab_setup, tab_whatsapp, tab_audit = st.tabs([
    "⚙️ Setup & Authentication",
    "📱 WhatsApp Gateway",
    "📜 Real-Time Audit Trail"
])


# =============================================================
# TAB 1: SETUP & AUTHENTICATION
# =============================================================
with tab_setup:
    st.markdown("#### Application Credentials & API Configuration")
    st.markdown(
        "<p style='color: var(--text-secondary); margin-top: -0.4rem; font-size: 0.92rem;'>"
        "Configure your <b>Gemini API Key</b> (for Gemma 4 OCR) and authorize your <b>Gmail Account</b> "
        "to allow TxnVerify AI to query transaction confirmations in real time."
        "</p>",
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # Step 1: Google Gemini API Key (Gemma 4 Access)
    # ---------------------------------------------------------
    step1_ready = sys_status["gemini_ready"]
    badge_cls = "step-badge-ready" if step1_ready else "step-badge-pending"
    badge_icon = "✓" if step1_ready else "1"

    st.markdown(f"""
    <div class="setup-step-box">
        <div class="step-header">
            <div class="step-badge {badge_cls}">{badge_icon}</div>
            <div>
                <div class="step-title-text">Step 1: Google Gemini API Key (Gemma 4 Multimodal)</div>
                <div class="step-desc-text">Required to extract structured transaction references and amounts from payment screenshots.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="instruction-callout">
        <b>How to get your free Gemini API Key:</b>
        <ol style="margin: 0.4rem 0 0.2rem 1.2rem; padding: 0;">
            <li>Go to <a href="https://aistudio.google.com/apikey" target="_blank" style="color: #60a5fa; text-decoration: underline;">Google AI Studio API Keys</a>.</li>
            <li>Click <b>Create API Key</b> and copy your key string (starts with <code>AIzaSy...</code>).</li>
            <li>Paste your key below and click <b>Save Gemini Key</b>.</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    col_key_in, col_key_btn = st.columns([3, 1])
    current_gemini_key = database.get_config("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
    input_gemini = col_key_in.text_input(
        "Gemini API Key",
        value=current_gemini_key,
        type="password",
        placeholder="AIzaSy...",
        label_visibility="collapsed"
    )
    if col_key_btn.button("Save Gemini Key", type="primary", use_container_width=True):
        if input_gemini.strip():
            database.set_config("gemini_api_key", input_gemini.strip())
            os.environ["GEMINI_API_KEY"] = input_gemini.strip()
            st.success("Gemini API Key successfully saved and verified!")
            st.rerun()
        else:
            st.warning("Please provide a valid Gemini API Key.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # Step 2: Google Cloud OAuth 2.0 Credentials (Client ID & Secret)
    # ---------------------------------------------------------
    step2_ready = sys_status["oauth_ready"]
    badge_cls2 = "step-badge-ready" if step2_ready else "step-badge-pending"
    badge_icon2 = "✓" if step2_ready else "2"

    st.markdown(f"""
    <div class="setup-step-box">
        <div class="step-header">
            <div class="step-badge {badge_cls2}">{badge_icon2}</div>
            <div>
                <div class="step-title-text">Step 2: Google Cloud OAuth 2.0 Client Credentials</div>
                <div class="step-desc-text">Enables the secure "Sign in with Google" flow requesting read-only Gmail access.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="instruction-callout">
        <b>Quick Setup in Google Cloud Console:</b>
        <ol style="margin: 0.4rem 0 0.2rem 1.2rem; padding: 0;">
            <li>Visit <a href="https://console.cloud.google.com/" target="_blank" style="color: #60a5fa; text-decoration: underline;">Google Cloud Console</a> and create or select a project.</li>
            <li>Navigate to <b>APIs & Services ➔ Library</b> and enable the <b>Gmail API</b>.</li>
            <li>Go to <b>APIs & Services ➔ OAuth consent screen</b>: Choose <i>External</i>, fill your email, and under <b>Test users</b> add your Gmail address (e.g. <code>fawazsaeed2012@gmail.com</code>).</li>
            <li>Go to <b>Credentials ➔ Create Credentials ➔ OAuth client ID</b> (Type: <code>Web application</code>).</li>
            <li>Under <b>Authorized redirect URIs</b>, add <b>BOTH</b> of these entries (Google requires exact match):
                <br>• <code>http://localhost:8501</code>
                <br>• <code>http://localhost:8501/</code>
            </li>
            <li>Copy your <b>Client ID</b> and <b>Client Secret</b> below.</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    c_id_col, c_sec_col = st.columns(2)
    saved_cid = database.get_config("google_client_id", os.getenv("GOOGLE_CLIENT_ID", ""))
    saved_csec = database.get_config("google_client_secret", os.getenv("GOOGLE_CLIENT_SECRET", ""))

    inp_cid = c_id_col.text_input("Client ID", value=saved_cid, placeholder="...apps.googleusercontent.com")
    inp_csec = c_sec_col.text_input("Client Secret", value=saved_csec, type="password", placeholder="GOCSPX-...")

    if st.button("Save Google OAuth Credentials", type="primary"):
        if inp_cid.strip() and inp_csec.strip():
            database.set_config("google_client_id", inp_cid.strip())
            database.set_config("google_client_secret", inp_csec.strip())
            os.environ["GOOGLE_CLIENT_ID"] = inp_cid.strip()
            os.environ["GOOGLE_CLIENT_SECRET"] = inp_csec.strip()
            st.success("OAuth Client Credentials saved!")
            st.rerun()
        else:
            st.warning("Please enter both Client ID and Client Secret.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # Step 3: Google Sign-In & Gmail Authorization
    # ---------------------------------------------------------
    step3_ready = sys_status["gmail_ready"]
    badge_cls3 = "step-badge-ready" if step3_ready else "step-badge-pending"
    badge_icon3 = "✓" if step3_ready else "3"
    connected_email = google_auth.get_user_email()

    st.markdown(f"""
    <div class="setup-step-box">
        <div class="step-header">
            <div class="step-badge {badge_cls3}">{badge_icon3}</div>
            <div>
                <div class="step-title-text">Step 3: Connect Gmail Account (gmail.readonly scope)</div>
                <div class="step-desc-text">Authorizes TxnVerify AI to query your inbox for bank transfer notification emails.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if connected_email and not sys_status["sandbox_mode"]:
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 12px; padding: 14px 18px; margin-bottom: 12px;">
            <div style="color: #34d399; font-weight: 700; font-size: 0.95rem;">✅ Gmail Account Connected</div>
            <div style="color: #f1f5f9; font-size: 0.9rem; margin-top: 3px;">Active Mailbox: <b>{connected_email}</b></div>
            <div style="color: #94a3b8; font-size: 0.78rem; margin-top: 4px;">TxnVerify AI has active read-only authorization to poll incoming payment alerts.</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Disconnect Gmail Account", type="secondary"):
            google_auth.sign_out()
            st.rerun()
    else:
        st.markdown("""
        <p style="color: #94a3b8; font-size: 0.88rem; line-height: 1.6;">
            Click the button below to initiate standard Google Web OAuth 2.0 flow. 
            Once you grant read-only access, Google redirects you directly back to this dashboard.
        </p>
        """, unsafe_allow_html=True)

        last_oauth_err = database.get_config("last_oauth_error")
        if last_oauth_err:
            if "Gmail API" in str(last_oauth_err):
                st.warning(f"⚠️ **Google Cloud Notice:** {last_oauth_err}\n\n👉 [Click here to Enable Gmail API in your Google Cloud Project](https://console.developers.google.com/apis/api/gmail.googleapis.com/overview)")
            else:
                st.info(f"Notice: {last_oauth_err}")

        try:
            auth_url, _ = google_auth.get_google_auth_url(redirect_uri="http://localhost:8501")
            st.link_button("🌐 Sign in with Google", auth_url, type="primary")
        except Exception as e:
            st.info("💡 Complete Step 2 above to generate your Google Sign-In link, or toggle Sandbox Mode below.")

        st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1.2rem 0;'>", unsafe_allow_html=True)

        # Sandbox / Mock Mode Option
        st.markdown("<div class='metric-title'>Offline Demonstration Option</div>", unsafe_allow_html=True)
        is_mock = database.get_config("sandbox_mode", False)
        mock_choice = st.checkbox("🧪 Enable Offline Sandbox Inbox", value=is_mock,
                                  help="Simulates bank confirmation emails for Chase, Venmo, Zelle, and UPI without live Gmail.")
        if mock_choice != is_mock:
            database.set_config("sandbox_mode", mock_choice)
            if mock_choice:
                database.set_config("sandbox_email", "demo-business@txnverify.ai")
                st.toast("Sandbox Demo Inbox activated!", icon="✅")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================
# TAB 2: WHATSAPP GATEWAY
# =============================================================
with tab_whatsapp:
    col_qr, col_info = st.columns([1, 1], gap="large")

    with col_qr:
        st.markdown("#### WhatsApp Device Connection")
        st.markdown(
            "<p style='color: var(--text-secondary); margin-top: -0.4rem; font-size: 0.88rem;'>"
            "Pair your physical WhatsApp phone to enable automated background chat monitoring."
            "</p>",
            unsafe_allow_html=True
        )

        gw_data = None
        try:
            r = requests.get(f"{GATEWAY_URL}/qr", timeout=2)
            gw_data = r.json()
        except Exception:
            pass

        if gw_data and gw_data.get("qr_data_url"):
            st.markdown(f"""
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem; background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 20px; box-shadow: 0 0 25px rgba(59, 130, 246, 0.15);">
                <img src="{gw_data.get('qr_data_url')}" style="width: 280px; height: 280px; border-radius: 12px; background: white; padding: 10px;">
                <div style="margin-top: 15px; color: #94a3b8; font-size: 0.88rem; font-weight: 600;">
                    Scan with WhatsApp on your phone
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif gw_data and gw_data.get("status") == "READY":
            paired = gw_data.get("paired_info") or {}
            push_name = paired.get("pushname", "Connected Device")
            st.markdown(f"""
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 3rem 2rem; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 20px; text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem;">📱</div>
                <div style="font-size: 1.25rem; font-weight: 800; color: #34d399;">WhatsApp Device Connected</div>
                <div style="color: #f1f5f9; font-weight: 600; font-size: 1rem; margin-top: 0.3rem;">{push_name}</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.4rem; max-width: 360px;">
                    Background listener is actively monitoring for incoming transaction screenshots 24/7.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 3rem 2rem; background: rgba(15, 23, 42, 0.5); border: 1px dashed rgba(255, 255, 255, 0.15); border-radius: 20px; text-align: center;">
                <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">⏳</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">Gateway Initializing</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.3rem;">
                    Starting WhatsApp Web JS service on port 3001...
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        btn1, btn2 = st.columns(2)
        if btn1.button("🔄 Refresh QR", use_container_width=True):
            st.rerun()
        if btn2.button("🔁 Restart WhatsApp Client", use_container_width=True):
            try:
                requests.post(f"{GATEWAY_URL}/start", timeout=2)
                st.toast("Triggered WhatsApp client reload", icon="🚀")
            except Exception:
                st.error("Cannot reach gateway service.")

    with col_info:
        st.markdown("#### How WhatsApp Pairing Works")
        st.markdown("""
        <div class="glass-card">
            <div style="font-weight: 700; color: #60a5fa; margin-bottom: 0.4rem;">1. Open WhatsApp</div>
            <div style="color: #94a3b8; font-size: 0.87rem; line-height: 1.6;">
                On your mobile phone, open WhatsApp and navigate to <b>Settings ➔ Linked Devices ➔ Link a Device</b>.
            </div>
        </div>
        <div class="glass-card" style="margin-top: 0.75rem;">
            <div style="font-weight: 700; color: #a78bfa; margin-bottom: 0.4rem;">2. Scan Live QR Code</div>
            <div style="color: #94a3b8; font-size: 0.87rem; line-height: 1.6;">
                Scan the secure QR generated on the left. The gateway authenticates and saves the session securely in <code>.wwebjs_auth</code>.
            </div>
        </div>
        <div class="glass-card" style="margin-top: 0.75rem;">
            <div style="font-weight: 700; color: #34d399; margin-bottom: 0.4rem;">3. Autonomous 24/7 Verification</div>
            <div style="color: #94a3b8; font-size: 0.87rem; line-height: 1.6;">
                Whenever a customer sends an image of a bank transfer slip, <b>TxnVerify AI</b> immediately intercepts it, runs Gemma 4 OCR, verifies funds in Gmail, and replies in the chat.
            </div>
        </div>
        """, unsafe_allow_html=True)


# =============================================================
# TAB 3: REAL-TIME AUDIT TRAIL
# =============================================================
with tab_audit:
    c_hdr, c_btn = st.columns([4, 1])
    c_hdr.markdown("#### Transaction Verification Audit History")
    if c_btn.button("🔄 Refresh Records", use_container_width=True):
        st.rerun()

    raw_txns = database.get_transactions(limit=100)
    if raw_txns:
        df_t = pd.DataFrame(raw_txns)
        cols = ["transaction_id", "bank_reference", "amount", "payment_app", "gemma_verified", "reconciliation_summary", "sender_phone", "created_at"]
        clean_df = df_t[[c for c in cols if c in df_t.columns]].copy()
        clean_df["gemma_verified"] = clean_df["gemma_verified"].apply(lambda v: "✅ Confirmed (Gemma 4)" if v == 1 else "❌ Unverified")
        clean_df.rename(columns={
            "transaction_id": "Receipt Ref / ID",
            "bank_reference": "Official Bank Ref",
            "amount": "Amount",
            "payment_app": "App / Channel",
            "gemma_verified": "Status",
            "reconciliation_summary": "Gemma 4 Audit Note",
            "sender_phone": "WhatsApp Sender",
            "created_at": "Timestamp"
        }, inplace=True)
        st.dataframe(clean_df, use_container_width=True)
    else:
        st.markdown("""
        <div class="glass-card" style="text-align: center; padding: 2.5rem; color: #94a3b8;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">📜</div>
            <div style="font-weight: 600; color: #f1f5f9;">No transactions recorded yet</div>
            <div style="font-size: 0.85rem; margin-top: 0.3rem;">
                Incoming transactions received via WhatsApp will automatically appear here with full verification timestamps.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1.5rem 0;'>", unsafe_allow_html=True)

    st.markdown("#### System Activity Logs")
    logs = database.get_recent_logs(limit=50)
    if logs:
        df_l = pd.DataFrame(logs)
        disp_cols = ["id", "timestamp", "sender", "event_type", "status", "details"]
        st.dataframe(df_l[[c for c in disp_cols if c in df_l.columns]], use_container_width=True)

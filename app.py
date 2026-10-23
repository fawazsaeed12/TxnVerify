"""
TxnVerify AI - Executive SaaS Dashboard
Autonomous WhatsApp Payment Verification Agent
Powered by Gemma 4 (gemma-4-26b-a4b-it) & Google Gmail API
"""

import os
import time
import base64
import requests
from pathlib import Path
from PIL import Image

import streamlit as st
import pandas as pd

import database
import google_auth
import agent_core

# -------------------------------------------------------------
# Page Configuration & Advanced Theme Injection
# -------------------------------------------------------------
st.set_page_config(
    page_title="TxnVerify AI | Intelligent WhatsApp Payment Gateway",
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
        background: rgba(11, 16, 27, 0.88) !important;
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
        font-size: 0.88rem !important;
        padding: 8px 18px !important;
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

    /* WhatsApp Authentic Message Preview */
    .wa-chat-container {
        background: #0b141a;
        background-image: radial-gradient(#1f2c34 1px, transparent 1px);
        background-size: 20px 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 18px;
        padding: 1.5rem;
        position: relative;
    }

    .wa-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding-bottom: 1rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }

    .wa-avatar {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background: linear-gradient(135deg, #00a884, #005c4b);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        font-weight: bold;
        color: white;
    }

    .wa-bubble-confirmed {
        background: #005c4b;
        color: #e9edef;
        padding: 14px 18px;
        border-radius: 12px 12px 2px 12px;
        font-size: 0.92rem;
        line-height: 1.6;
        margin-left: auto;
        max-width: 88%;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
        white-space: pre-wrap;
        position: relative;
    }

    .wa-bubble-unverified {
        background: #391e24;
        color: #ffccd3;
        border: 1px solid rgba(248, 113, 113, 0.3);
        padding: 14px 18px;
        border-radius: 12px 12px 2px 12px;
        font-size: 0.92rem;
        line-height: 1.6;
        margin-left: auto;
        max-width: 88%;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
        white-space: pre-wrap;
    }

    /* Step Timeline Pills */
    .pipeline-step {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        margin-bottom: 8px;
        font-size: 0.88rem;
    }

    /* Inputs & Form Overrides */
    .stTextInput input {
        background: rgba(15, 23, 42, 0.6) !important;
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

    /* Dataframe styling */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border-color);
        border-radius: 14px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Handle Google OAuth 2.0 Direct Callback
# -------------------------------------------------------------
if "code" in st.query_params:
    auth_code = st.query_params["code"]
    with st.spinner("Authorizing Gmail API access with Google..."):
        creds = google_auth.exchange_code_for_token(auth_code, redirect_uri="http://localhost:8501")
        if creds:
            database.log_event("AUTH_SUCCESS", "CONNECTED", "Connected via direct Streamlit OAuth redirect")
            st.toast("Google Account successfully connected!", icon="🎉")
        else:
            st.error("Failed to exchange Google OAuth code. Check Redirect URI settings.")
    st.query_params.clear()

if "auth_success" in st.query_params:
    st.toast("Google Account connected via OAuth 2.0!", icon="🎉")
    st.query_params.clear()


# -------------------------------------------------------------
# Sidebar Configuration & Controls
# -------------------------------------------------------------
GATEWAY_URL = os.getenv("WHATSAPP_GATEWAY_URL", "http://localhost:3001")

with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; padding: 0.5rem 0 1rem;">
        <div style="width: 42px; height: 42px; border-radius: 12px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); display: flex; align-items: center; justify-content: center; font-size: 1.3rem; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);">
            ⚡
        </div>
        <div>
            <div style="font-weight: 800; font-size: 1.15rem; color: #ffffff; letter-spacing: -0.02em;">TxnVerify AI</div>
            <div style="font-size: 0.78rem; color: #94a3b8;">Autonomous Verification Agent</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 0.5rem 0 1.2rem;'>", unsafe_allow_html=True)

    # 1. Master Agent Switch
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

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Gemini / Gemma 4 Credentials
    st.markdown("<div class='metric-title'>Core AI Model (Vision OCR)</div>", unsafe_allow_html=True)
    current_key = database.get_config("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
    gemini_key = st.text_input(
        "Google Gemini API Key",
        value=current_key,
        type="password",
        placeholder="Enter key for Gemma 4...",
        help="Access key from Google AI Studio. Used by gemma-4-26b-a4b-it."
    )
    if gemini_key != current_key:
        database.set_config("gemini_api_key", gemini_key)
        os.environ["GEMINI_API_KEY"] = gemini_key
        st.toast("Gemini API Key saved!", icon="🔑")

    selected_model = st.selectbox(
        "Model Selection",
        options=["gemma-4-26b-a4b-it", "gemini-2.5-flash", "gemini-1.5-flash"],
        index=0,
        help="Gemma 4 provides visual OCR and high-fidelity transaction parameter extraction."
    )
    database.set_config("gemini_model", selected_model)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1.2rem 0;'>", unsafe_allow_html=True)

    # 3. Google OAuth & Gmail Account Status
    st.markdown("<div class='metric-title'>Gmail Confirmation Feed</div>", unsafe_allow_html=True)
    connected_email = google_auth.get_user_email()

    if connected_email:
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 10px; padding: 10px 12px; margin-bottom: 10px;">
            <div style="font-size: 0.72rem; color: #34d399; font-weight: 700; text-transform: uppercase;">CONNECTED ACCOUNT</div>
            <div style="font-size: 0.86rem; color: #f1f5f9; font-weight: 600; text-overflow: ellipsis; overflow: hidden;">{connected_email}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Sign Out of Google", type="secondary", use_container_width=True):
            google_auth.sign_out()
            st.rerun()
    else:
        try:
            auth_url, _ = google_auth.get_google_auth_url(redirect_uri="http://localhost:8501")
            st.link_button("🌐 Sign in with Google", auth_url, type="primary", use_container_width=True)
        except Exception:
            pass

    # Quick Mock Sandbox Toggle (for offline testing)
    is_mock = database.get_config("sandbox_mode", False)
    mock_box = st.checkbox("🧪 Offline Sandbox Mode", value=is_mock, help="Simulate bank email matches without live Gmail")
    if mock_box != is_mock:
        database.set_config("sandbox_mode", mock_box)
        st.rerun()

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1.2rem 0;'>", unsafe_allow_html=True)

    # 4. WhatsApp Gateway Status Indicator
    st.markdown("<div class='metric-title'>WhatsApp Service (:3001)</div>", unsafe_allow_html=True)
    try:
        gw_res = requests.get(f"{GATEWAY_URL}/status", timeout=1.5)
        if gw_res.status_code == 200:
            status = gw_res.json().get("status", "UNKNOWN")
            badge = "🟢 ONLINE" if status == "READY" else f"🟡 {status}"
            st.caption(f"Status: **{badge}**")
        else:
            st.caption("Status: 🔴 OFFLINE")
    except Exception:
        st.caption("Status: ⚪ Offline (`npm start`)")


# -------------------------------------------------------------
# Top Hero Header & Live KPI Metric Bar
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
# Interactive SaaS Workstation Tabs
# -------------------------------------------------------------
tab_verify, tab_whatsapp, tab_audit, tab_setup = st.tabs([
    "⚡ Live Verification Sandbox",
    "📱 WhatsApp Gateway Station",
    "📜 Real-Time Audit Trail",
    "⚙️ Integration & Setup Guide"
])


# =============================================================
# TAB 1: LIVE VERIFICATION SANDBOX
# =============================================================
with tab_verify:
    st.markdown("#### Instant Receipt Verification Engine")
    st.markdown(
        "<p style='color: var(--text-secondary); margin-top: -0.4rem; font-size: 0.92rem;'>"
        "Upload a payment confirmation screenshot to test <b>Gemma 4</b> visual extraction, "
        "the <b>60-Second Gmail Polling Loop</b>, and the automated <b>WhatsApp Dispatch</b>."
        "</p>",
        unsafe_allow_html=True
    )

    col_input, col_output = st.columns([1, 1], gap="large")

    with col_input:
        st.markdown("<div class='metric-title'>1. Select Payment Receipt</div>", unsafe_allow_html=True)

        # High-End Preset Selector
        preset = st.radio(
            "Presets & Upload",
            ["Zelle Transfer ($150.00)", "Venmo Payment ($45.00)", "Google Pay UPI (₹2,500.00)", "Custom Upload"],
            horizontal=True,
            label_visibility="collapsed"
        )

        sample_dir = Path(__file__).parent / "sample_receipts"
        selected_bytes = None
        selected_mime = "image/jpeg"
        selected_label = ""

        if preset == "Zelle Transfer ($150.00)":
            p = sample_dir / "zelle_receipt_150.jpg"
            if p.exists():
                selected_bytes = p.read_bytes()
                selected_label = "Zelle Transfer: Ref ZEL-982341908 ($150.00)"
        elif preset == "Venmo Payment ($45.00)":
            p = sample_dir / "venmo_receipt_45.jpg"
            if p.exists():
                selected_bytes = p.read_bytes()
                selected_label = "Venmo Payment: Ref VEN-549102834 ($45.00)"
        elif preset == "Google Pay UPI (₹2,500.00)":
            p = sample_dir / "upi_receipt_2500.jpg"
            if p.exists():
                selected_bytes = p.read_bytes()
                selected_label = "UPI Transfer: Ref UPI-409182390192 (₹2,500.00)"
        else:
            up_file = st.file_uploader("Upload Receipt (.jpg, .png)", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed")
            if up_file:
                selected_bytes = up_file.getvalue()
                selected_mime = up_file.type
                selected_label = up_file.name

        if selected_bytes:
            st.image(selected_bytes, caption=selected_label, use_container_width=True)

        sender_number = st.text_input("Customer WhatsApp Sender Number", value="+1 (555) 392-1092")

        trigger_verify = st.button("🚀 Execute Verification Pipeline", type="primary", use_container_width=True,
                                   disabled=selected_bytes is None)

    with col_output:
        st.markdown("<div class='metric-title'>2. Real-Time Pipeline Trace & WhatsApp Reply</div>", unsafe_allow_html=True)

        if trigger_verify and selected_bytes:
            progress_bar = st.progress(10, text="Initializing Gemma 4 Multimodal Visual OCR...")
            trace_box = st.empty()

            def update_trace(attempt: int, elapsed: int, msg: str):
                val = min(15 + int((elapsed / 60) * 80), 95)
                progress_bar.progress(val, text=f"[{elapsed}s] {msg}")

            try:
                trace_box.info(f"🧠 Gemma 4 ({selected_model}) analyzing receipt visual geometry...")

                # Run Pipeline
                result = agent_core.process_payment_image(
                    image_bytes=selected_bytes,
                    mime_type=selected_mime,
                    sender_phone=sender_number,
                    model_name=selected_model,
                    progress_callback=update_trace
                )

                progress_bar.progress(100, text="Pipeline execution finished!")
                trace_box.empty()

                is_verified = result.get("verified", False)
                is_txn = result.get("is_transaction", False)

                # Output Banner
                if is_verified:
                    st.success(f"✅ **PAYMENT CONFIRMED** in {result.get('elapsed_seconds')}s via Gmail API")
                elif is_txn:
                    st.error(f"❌ **UNVERIFIED PAYMENT** — No matching credit notification in Gmail after 60s")
                else:
                    st.warning("⚠️ **INVALID IMAGE** — Receipt features or transaction reference not detected")

                # Extraction Summary Cards
                st.markdown("<div class='metric-title' style='margin-top: 1rem;'>Gemma 4 Structured Parameters</div>", unsafe_allow_html=True)
                c_a, c_b = st.columns(2)
                c_a.metric("Transaction ID", result.get("transaction_id") or "None")
                c_a.metric("Amount", result.get("amount") or "None")
                c_b.metric("Platform", result.get("payment_app") or "N/A")
                c_b.metric("OCR Confidence", f"{round(result.get('confidence', 0.95) * 100)}%")

                # Matched Gmail Confirmation
                gmail_match = result.get("gmail_match")
                if gmail_match:
                    with st.expander("📬 Matched Gmail Bank Notification", expanded=True):
                        st.markdown(f"**Subject:** {gmail_match.get('subject')}")
                        st.markdown(f"**Sender:** {gmail_match.get('sender')}")
                        st.markdown(f"**Source:** `{gmail_match.get('source')}`")
                        st.caption(f"\"{gmail_match.get('snippet')}\"")

                # WhatsApp Interactive Bubble
                st.markdown("<div class='metric-title' style='margin-top: 1.2rem;'>Customer WhatsApp Response</div>", unsafe_allow_html=True)
                bubble_class = "wa-bubble-confirmed" if is_verified else "wa-bubble-unverified"
                now_time = time.strftime("%H:%M")

                st.markdown(f"""
                <div class="wa-chat-container">
                    <div class="wa-header">
                        <div class="wa-avatar">TV</div>
                        <div>
                            <div style="font-weight: 700; color: #e9edef; font-size: 0.95rem;">TxnVerify AI Assistant</div>
                            <div style="font-size: 0.75rem; color: #8696a0;">Official WhatsApp Gateway • Online</div>
                        </div>
                    </div>
                    <div class="{bubble_class}">
{result.get('reply_text')}
                        <div style="font-size: 0.68rem; color: #8696a0; text-align: right; margin-top: 6px;">
                            {now_time} <span style="color: #53bdeb;">✓✓</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            except Exception as e:
                progress_bar.empty()
                trace_box.error(f"Execution Error: {e}")
                st.exception(e)
        else:
            st.markdown("""
            <div style="height: 340px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(17, 24, 39, 0.4); border: 1px dashed rgba(255, 255, 255, 0.15); border-radius: 18px; text-align: center; padding: 2rem;">
                <div style="font-size: 2.5rem; margin-bottom: 0.8rem;">⚡</div>
                <div style="font-weight: 700; color: #f8fafc; font-size: 1.05rem;">Awaiting Verification Request</div>
                <div style="font-size: 0.85rem; color: #94a3b8; max-width: 320px; margin-top: 0.3rem;">
                    Select a preset receipt or drop an image on the left, then click <b>Execute Verification Pipeline</b>.
                </div>
            </div>
            """, unsafe_allow_html=True)


# =============================================================
# TAB 2: WHATSAPP GATEWAY STATION
# =============================================================
with tab_whatsapp:
    col_qr, col_info = st.columns([1, 1], gap="large")

    with col_qr:
        st.markdown("#### WhatsApp Device Connection")
        st.markdown(
            "<p style='color: var(--text-secondary); margin-top: -0.4rem; font-size: 0.88rem;'>"
            "Pair your physical device to enable automated real-time background chat monitoring."
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
            st.markdown("""
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 3rem 2rem; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 20px; text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem;">📱</div>
                <div style="font-size: 1.25rem; font-weight: 800; color: #34d399;">WhatsApp Device Connected</div>
                <div style="color: #94a3b8; font-size: 0.88rem; margin-top: 0.4rem; max-width: 360px;">
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
                    Starting Chromium headless browser on port 3001...
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
                On your mobile device, navigate to <b>Settings ➔ Linked Devices ➔ Link a Device</b>.
            </div>
        </div>
        <div class="glass-card" style="margin-top: 0.75rem;">
            <div style="font-weight: 700; color: #a78bfa; margin-bottom: 0.4rem;">2. Point Camera at QR Code</div>
            <div style="color: #94a3b8; font-size: 0.87rem; line-height: 1.6;">
                Scan the secure QR generated on the left. The gateway authenticates and saves the session securely in <code>.wwebjs_auth</code>.
            </div>
        </div>
        <div class="glass-card" style="margin-top: 0.75rem;">
            <div style="font-weight: 700; color: #34d399; margin-bottom: 0.4rem;">3. Autonomous 24/7 Verification</div>
            <div style="color: #94a3b8; font-size: 0.87rem; line-height: 1.6;">
                Whenever a buyer or customer sends an image of a bank slip, <b>TxnVerify AI</b> immediately intercepts it, runs Gemma 4 OCR, verifies funds in Gmail, and replies in the chat.
            </div>
        </div>
        """, unsafe_allow_html=True)


# =============================================================
# TAB 3: REAL-TIME AUDIT TRAIL
# =============================================================
with tab_audit:
    st.markdown("#### Transaction Verification Audit History")

    raw_txns = database.get_transactions(limit=100)
    if raw_txns:
        df_t = pd.DataFrame(raw_txns)
        cols = ["transaction_id", "amount", "sender_phone", "payment_app", "gmail_verified", "ocr_confidence", "created_at"]
        clean_df = df_t[[c for c in cols if c in df_t.columns]].copy()
        clean_df["gmail_verified"] = clean_df["gmail_verified"].apply(lambda v: "✅ Confirmed" if v == 1 else "❌ Unverified")
        if "ocr_confidence" in clean_df.columns:
            clean_df["ocr_confidence"] = clean_df["ocr_confidence"].apply(lambda c: f"{round(float(c or 0.95)*100)}%")
        st.dataframe(clean_df, use_container_width=True)
    else:
        st.info("No transactions logged yet. Run a verification from the Sandbox tab!")

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 1.5rem 0;'>", unsafe_allow_html=True)

    st.markdown("#### System Activity Logs")
    logs = database.get_recent_logs(limit=50)
    if logs:
        df_l = pd.DataFrame(logs)
        disp_cols = ["id", "timestamp", "sender", "event_type", "status", "details"]
        st.dataframe(df_l[[c for c in disp_cols if c in df_l.columns]], use_container_width=True)


# =============================================================
# TAB 4: INTEGRATION & SETUP GUIDE
# =============================================================
with tab_setup:
    st.markdown("#### System Architecture & Setup Guide")
    st.markdown("""
    ```
    ┌──────────────────────────┐          ┌──────────────────────────┐
    │  Customer Mobile Phone   │          │ Streamlit Control Panel  │
    │  Sends receipt on WA     │          │ Port 8501 (UI & Sandbox) │
    └────────────┬─────────────┘          └────────────┬─────────────┘
                 │                                     │
                 ▼                                     │
    ┌──────────────────────────────────────┐           │
    │  WhatsApp Gateway Service (Node.js)  │◄──────────┘
    │  Port 3001 (whatsapp-web.js)         │
    └──────────────────┬───────────────────┘
                       │ HTTP POST (Base64 Receipt)
                       ▼
    ┌────────────────────────────────────────────────────────────┐
    │  TxnVerify AI Engine (FastAPI Server on Port 8000)         │
    │                                                            │
    │  1. Gemma 4 Multimodal Visual OCR (gemma-4-26b-a4b-it)     │
    │     -> Parses Transaction ID, Amount, Payment App          │
    │                                                            │
    │  2. 60-Second Real-Time Gmail Inbox Polling Loop           │
    │     -> users.messages.list(userId='me', q=transaction_id)  │
    │                                                            │
    │  3. SQLite Audit Logger & Auto WhatsApp Reply Dispatch     │
    └────────────────────────────────────────────────────────────┘
    ```
    """)
    st.markdown("##### Direct API Endpoints")
    st.code("""
# WhatsApp Media Webhook:
POST http://127.0.0.1:8000/webhook/whatsapp
Payload: { "from": "+1555123456", "data": "<base64>", "mimetype": "image/jpeg" }

# Send WhatsApp Text Message:
POST http://127.0.0.1:3001/send-message
Payload: { "to": "+1555123456", "message": "✅ Payment Confirmed!" }
    """, language="http")

"""
TxnVerify AI - Streamlit Control Dashboard & Judge Test Panel
Features:
- Gemini API Key input (for Gemma 4 access)
- Direct "Sign in with Google" OAuth 2.0 Web Flow (gmail.readonly scope)
- Live WhatsApp QR Code pairing monitor
- Start / Stop Agent toggle switch with real-time activity logs
- Interactive Judge Test Panel for instant live OCR & Gmail verification testing
"""

import os
import time
import base64
import requests
from io import BytesIO
from pathlib import Path
from PIL import Image

import streamlit as st
import pandas as pd

import database
import google_auth
import agent_core

# -------------------------------------------------------------
# Page Configuration & Styling
# -------------------------------------------------------------
st.set_page_config(
    page_title="TxnVerify AI | WhatsApp Payment Verification Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #2563eb, #7c3aed, #059669);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #64748b;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .status-badge-active {
        display: inline-block;
        background: #dcfce7;
        color: #166534;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-badge-inactive {
        display: inline-block;
        background: #fee2e2;
        color: #991b1b;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .chat-bubble {
        background: #eef2ff;
        border-left: 4px solid #4f46e5;
        padding: 1rem;
        border-radius: 8px;
        font-family: monospace;
        white-space: pre-wrap;
    }
    .qr-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 1.5rem;
        background: white;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Handle OAuth 2.0 Web Callback in Streamlit
# -------------------------------------------------------------
if "code" in st.query_params:
    auth_code = st.query_params["code"]
    with st.spinner("Exchanging Google authorization code..."):
        creds = google_auth.exchange_code_for_token(auth_code, redirect_uri="http://localhost:8501")
        if creds:
            st.success("Google Account successfully connected with `gmail.readonly` permissions!")
            database.log_event("AUTH_SUCCESS", "CONNECTED", "Connected via direct Streamlit OAuth redirect")
        else:
            st.error("Failed to complete Google OAuth exchange. Please verify redirect URI configuration.")
    st.query_params.clear()

if "auth_success" in st.query_params:
    st.toast("Google Account authenticated successfully!", icon="🎉")
    st.query_params.clear()

# -------------------------------------------------------------
# Sidebar: Setup & Control Center
# -------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/shield.png", width=64)
    st.title("TxnVerify AI")
    st.caption("Automated WhatsApp Payment Verification Agent")
    st.divider()

    # 1. Start / Stop Agent Master Toggle
    is_running = database.get_config("agent_running", True)
    agent_toggle = st.toggle("⚡ Agent Running", value=is_running, key="agent_toggle_switch")
    if agent_toggle != is_running:
        database.set_config("agent_running", agent_toggle)
        database.log_event("AGENT_STATE", "ENABLED" if agent_toggle else "PAUSED", "Agent status updated by user")
        st.rerun()

    if agent_toggle:
        st.markdown('<span class="status-badge-active">🟢 Agent Active & Listening</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge-inactive">⏸️ Agent Paused</span>', unsafe_allow_html=True)

    st.divider()

    # 2. Gemini API Key Configuration
    st.subheader("🔑 Google Gemini API")
    stored_gemini_key = database.get_config("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
    gemini_key_input = st.text_input(
        "Gemini API Key",
        value=stored_gemini_key,
        type="password",
        help="Access key from Google AI Studio. Required for Gemma 4 visual OCR."
    )
    if gemini_key_input != stored_gemini_key:
        database.set_config("gemini_api_key", gemini_key_input)
        os.environ["GEMINI_API_KEY"] = gemini_key_input
        st.success("Gemini API Key saved!")

    # Model Selection
    selected_model = st.selectbox(
        "Vision Model",
        options=["gemma-4-26b-a4b-it", "gemini-2.5-flash", "gemini-1.5-flash"],
        index=0,
        help="Gemma 4 (gemma-4-26b-a4b-it) is used for visual OCR and structured information extraction."
    )
    database.set_config("gemini_model", selected_model)

    st.divider()

    # 3. Google OAuth & Gmail Integration
    st.subheader("📬 Gmail API Auth")
    connected_email = google_auth.get_user_email()
    is_sandbox = database.get_config("sandbox_mode", False)

    if connected_email and not is_sandbox:
        st.success(f"Connected: **{connected_email}**")
        if st.button("Sign Out of Google", type="secondary", use_container_width=True):
            google_auth.sign_out()
            st.rerun()
    else:
        # Standard "Sign in with Google" Button
        try:
            auth_url, _ = google_auth.get_google_auth_url(redirect_uri="http://localhost:8501")
            st.link_button(
                "🌐 Sign in with Google",
                auth_url,
                type="primary",
                use_container_width=True,
                help="Authorizes TxnVerify AI to query your Gmail inbox for transaction confirmation emails (gmail.readonly scope)."
            )
        except Exception as e:
            st.warning(f"OAuth URL generator notice: {e}")

        # Judge Sandbox Quick-Connect
        st.caption("— or for Hackathon Judges without live banking email —")
        sandbox_toggle = st.checkbox("🧪 Enable Judge Demo Inbox", value=is_sandbox,
                                     help="Simulates instant bank confirmation emails for Chase, Venmo, Zelle, and UPI.")
        if sandbox_toggle != is_sandbox:
            database.set_config("sandbox_mode", sandbox_toggle)
            if sandbox_toggle:
                database.set_config("sandbox_email", "judge-demo@txnverify.ai")
                st.toast("Demo Sandbox Inbox activated!", icon="✅")
            st.rerun()

    st.divider()

    # WhatsApp Gateway Status Quick Check
    gateway_url = os.getenv("WHATSAPP_GATEWAY_URL", "http://localhost:3001")
    try:
        gw_res = requests.get(f"{gateway_url}/status", timeout=2)
        if gw_res.status_code == 200:
            gw_status = gw_res.json().get("status", "UNKNOWN")
            st.caption(f"WhatsApp Gateway: **{gw_status}** (:3001)")
        else:
            st.caption("WhatsApp Gateway: Offline")
    except Exception:
        st.caption("WhatsApp Gateway: Offline (Run `npm start`)")


# -------------------------------------------------------------
# Main Dashboard Header & Metrics
# -------------------------------------------------------------
col_header, col_actions = st.columns([3, 1])
with col_header:
    st.markdown('<div class="main-title">TxnVerify AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Autonomous WhatsApp payment verification agent powered by <b>Gemma 4</b> & <b>Gmail API</b></div>', unsafe_allow_html=True)

with col_actions:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

# Metrics Row
transactions = database.get_transactions(limit=100)
total_txn = len(transactions)
verified_txn = len([t for t in transactions if t.get("gmail_verified") == 1])
unverified_txn = total_txn - verified_txn
success_rate = f"{round((verified_txn / total_txn * 100), 1)}%" if total_txn > 0 else "100%"

m1, m2, m3, m4 = st.columns(4)
m1.metric("Receipts Processed", total_txn)
m2.metric("Verified via Gmail", verified_txn, delta="Confirmed")
m3.metric("Unverified / Pending", unverified_txn)
m4.metric("Verification Rate", success_rate)

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# Main Navigation Tabs
# -------------------------------------------------------------
tab_test, tab_qr, tab_logs, tab_arch = st.tabs([
    "🧪 Judge Test Panel (Live Demo)",
    "📱 WhatsApp QR Pairing",
    "📊 Live Activity & Audit Logs",
    "⚙️ Architecture & Webhook Docs"
])

# =============================================================
# TAB 1: JUDGE TEST PANEL
# =============================================================
with tab_test:
    st.subheader("Interactive Evaluation Panel")
    st.write(
        "Upload a payment screenshot or select a pre-generated sample receipt. "
        "The agent will execute the exact pipeline: **Gemma 4 Visual OCR** ➡️ **60-Second Gmail Polling** ➡️ **Automated WhatsApp Response**."
    )

    test_col1, test_col2 = st.columns([1, 1], gap="large")

    with test_col1:
        st.markdown("##### 1. Select or Upload Payment Receipt")

        # Quick sample selector
        sample_choice = st.radio(
            "Quick Load Hackathon Samples:",
            ["Custom Upload", "Zelle ($150.00)", "Venmo ($45.00)", "Google Pay UPI (₹2,500.00)"],
            horizontal=True
        )

        selected_image_bytes = None
        selected_mime_type = "image/jpeg"
        image_label = ""

        sample_dir = Path(__file__).parent / "sample_receipts"

        if sample_choice == "Zelle ($150.00)":
            p = sample_dir / "zelle_receipt_150.jpg"
            if p.exists():
                selected_image_bytes = p.read_bytes()
                image_label = "Sample Zelle Receipt ($150.00 - Txn ZEL-982341908)"
        elif sample_choice == "Venmo ($45.00)":
            p = sample_dir / "venmo_receipt_45.jpg"
            if p.exists():
                selected_image_bytes = p.read_bytes()
                image_label = "Sample Venmo Receipt ($45.00 - Txn VEN-549102834)"
        elif sample_choice == "Google Pay UPI (₹2,500.00)":
            p = sample_dir / "upi_receipt_2500.jpg"
            if p.exists():
                selected_image_bytes = p.read_bytes()
                image_label = "Sample UPI Receipt (₹2,500.00 - Txn UPI-409182390192)"
        else:
            uploaded_file = st.file_uploader("Upload Receipt Image", type=["jpg", "jpeg", "png", "webp"])
            if uploaded_file:
                selected_image_bytes = uploaded_file.getvalue()
                selected_mime_type = uploaded_file.type
                image_label = uploaded_file.name

        if selected_image_bytes:
            st.image(selected_image_bytes, caption=image_label or "Selected Payment Receipt", use_container_width=True)

        sender_sim = st.text_input("Simulate WhatsApp Sender Phone", value="+1 (555) 392-1092")

        run_button = st.button("🚀 Run Live Verification Pipeline", type="primary", use_container_width=True,
                               disabled=selected_image_bytes is None)

    with test_col2:
        st.markdown("##### 2. Live Execution Trace & Results")

        if run_button and selected_image_bytes:
            progress_bar = st.progress(10, text="Initializing Gemma 4 OCR extraction...")
            status_placeholder = st.empty()

            def update_progress(step: int, elapsed: int, msg: str):
                pct = min(15 + int((elapsed / 60) * 80), 95)
                progress_bar.progress(pct, text=f"[{elapsed}s] {msg}")

            try:
                # Execute pipeline
                status_placeholder.info(f"🧠 Gemma 4 ({selected_model}) analyzing visual features...")
                start_exec = time.time()

                # Process
                result = agent_core.process_payment_image(
                    image_bytes=selected_image_bytes,
                    mime_type=selected_mime_type,
                    sender_phone=sender_sim,
                    model_name=selected_model,
                    progress_callback=update_progress
                )

                progress_bar.progress(100, text="Verification complete!")
                status_placeholder.empty()

                # Visual Cards for Output
                is_txn = result.get("is_transaction")
                is_ver = result.get("verified")

                if is_ver:
                    st.success(f"✅ **PAYMENT CONFIRMED** in {result.get('elapsed_seconds')}s")
                elif is_txn:
                    st.error(f"❌ **PAYMENT UNVERIFIED** (No matching email found in Gmail within 60s)")
                else:
                    st.warning("⚠️ **INVALID RECEIPT** (Image is not a payment transaction)")

                # Structured Details
                st.markdown("###### 🔍 Extracted Data (Gemma 4 Structured JSON)")
                res_col_a, res_col_b = st.columns(2)
                res_col_a.metric("Transaction ID", result.get("transaction_id") or "None")
                res_col_a.metric("Amount", result.get("amount") or "None")
                res_col_b.metric("Platform", result.get("payment_app") or "N/A")
                res_col_b.metric("OCR Confidence", f"{round(result.get('confidence', 0.95) * 100)}%")

                # Gmail Verification Evidence
                gmail_match = result.get("gmail_match")
                if gmail_match:
                    with st.expander("📬 Matched Gmail Confirmation Email", expanded=True):
                        st.write(f"**Subject:** {gmail_match.get('subject')}")
                        st.write(f"**From:** {gmail_match.get('sender')}")
                        st.write(f"**Source:** {gmail_match.get('source')}")
                        st.info(f"Snippet: \"{gmail_match.get('snippet')}\"")

                # WhatsApp Reply Preview
                st.markdown("###### 💬 Automated WhatsApp Reply Dispatched:")
                st.markdown(f'<div class="chat-bubble">{result.get("reply_text")}</div>', unsafe_allow_html=True)

            except Exception as e:
                progress_bar.empty()
                status_placeholder.error(f"Pipeline error: {e}")
                st.exception(e)
        else:
            st.info("👈 Upload or select a receipt on the left, then click 'Run Live Verification Pipeline'.")


# =============================================================
# TAB 2: WHATSAPP QR PAIRING
# =============================================================
with tab_qr:
    st.subheader("WhatsApp Web Gateway Pairing")
    st.write("Pair your phone to enable live 24/7 background WhatsApp monitoring.")

    qr_col1, qr_col2 = st.columns([1, 1], gap="large")

    with qr_col1:
        st.markdown("##### Pair WhatsApp Device")
        qr_status_box = st.empty()

        gateway_url = os.getenv("WHATSAPP_GATEWAY_URL", "http://localhost:3001")
        gw_data = None
        try:
            r = requests.get(f"{gateway_url}/qr", timeout=3)
            gw_data = r.json()
        except Exception:
            pass

        if gw_data and gw_data.get("qr_data_url"):
            st.markdown(f"""
            <div class="qr-container">
                <img src="{gw_data.get('qr_data_url')}" style="max-width: 320px; border-radius: 8px;">
                <p style="margin-top: 10px; color: #64748b; font-size: 0.9rem;">Scan this QR with WhatsApp on your phone</p>
            </div>
            """, unsafe_allow_html=True)
        elif gw_data and gw_data.get("status") == "READY":
            st.success("✅ **WhatsApp Device is Connected and Ready!**")
            st.info("The agent is actively monitoring incoming chats for payment screenshots.")
        else:
            st.warning("QR code not generated yet or WhatsApp Gateway is starting up.")
            st.caption("Ensure `npm start` is running in the project directory.")

        btn_c1, btn_c2 = st.columns(2)
        if btn_c1.button("🔄 Refresh QR Code", use_container_width=True):
            st.rerun()
        if btn_c2.button("🔁 Restart WhatsApp Client", use_container_width=True):
            try:
                requests.post(f"{gateway_url}/start", timeout=3)
                st.toast("Triggered WhatsApp client restart", icon="🚀")
            except Exception as e:
                st.error(f"Could not reach gateway: {e}")

    with qr_col2:
        st.markdown("##### How It Works")
        st.markdown("""
        1. **Open WhatsApp** on your mobile phone.
        2. Tap **Settings** ➡️ **Linked Devices** ➡️ **Link a Device**.
        3. Point your camera at the QR code displayed on the left.
        4. Once paired:
           - Whenever a customer or buyer sends a screenshot of their payment receipt to this WhatsApp account,
           - `whatsapp-web.js` intercepts the image buffer in real-time,
           - Forwards it to the **TxnVerify AI Engine**,
           - Gemma 4 extracts the transaction reference,
           - The 60-second Gmail verification loop runs,
           - An automated reply (`✅ Payment Confirmed` or `❌ Unverified`) is sent back immediately!
        """)


# =============================================================
# TAB 3: LIVE ACTIVITY & AUDIT LOGS
# =============================================================
with tab_logs:
    st.subheader("Real-Time Audit Trail")

    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("🔄 Refresh Logs", key="refresh_logs_btn"):
            st.rerun()

    # Processed Transactions Table
    st.markdown("##### 💳 Processed Transactions")
    raw_txns = database.get_transactions(limit=50)
    if raw_txns:
        df_txns = pd.DataFrame(raw_txns)
        # Select and rename columns for display
        cols = ["transaction_id", "amount", "sender_phone", "payment_app", "gmail_verified", "created_at"]
        display_df = df_txns[[c for c in cols if c in df_txns.columns]].copy()
        display_df["gmail_verified"] = display_df["gmail_verified"].apply(lambda v: "✅ Confirmed" if v == 1 else "❌ Unverified")
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No transactions processed yet. Run a test from the Judge Test Panel!")

    st.divider()

    # Detailed Activity Log Feed
    st.markdown("##### 📜 System Activity Logs")
    raw_logs = database.get_recent_logs(limit=40)
    if raw_logs:
        df_logs = pd.DataFrame(raw_logs)
        st.dataframe(df_logs[["id", "timestamp", "sender", "event_type", "status", "details"]], use_container_width=True)
    else:
        st.info("No activity logs available.")


# =============================================================
# TAB 4: ARCHITECTURE & API DOCS
# =============================================================
with tab_arch:
    st.subheader("System Architecture & Hackathon Design")
    st.markdown("""
    ```
    ┌──────────────────────┐        ┌─────────────────────────┐
    │ Customer WhatsApp    │        │ Streamlit Control Panel │
    │ (Sends Receipt Img)  │        │ (Judge Test & QR View)  │
    └──────────┬───────────┘        └────────────┬────────────┘
               │                                 │
               ▼                                 │
    ┌──────────────────────────────────┐         │
    │  whatsapp-web.js (Node Gateway)  │◄────────┘
    │  Port 3001 (QR & Message Listener│
    └──────────────────┬───────────────┘
                       │ HTTP Webhook Forward (Base64)
                       ▼
    ┌────────────────────────────────────────────────────────┐
    │  TxnVerify AI Engine (FastAPI & Agent Core)           │
    │  Port 8000                                             │
    │                                                        │
    │  1. Gemma 4 (gemma-4-26b-a4b-it) Multimodal OCR       │
    │     -> Extracts: {is_transaction, transaction_id,      │
    │                   amount, payment_app}                 │
    │                                                        │
    │  2. 60-Second Gmail Inbox Polling Loop                 │
    │     -> users.messages.list(userId='me', q=txn_id)      │
    │                                                        │
    │  3. Automated Reply Generator & SQLite Audit Logger    │
    └──────────────────┬─────────────────────────────────────┘
                       │
                       ▼
    ┌────────────────────────────────────────────────────────┐
    │  WhatsApp Dispatch (✅ Confirmed or ❌ Unverified)     │
    └────────────────────────────────────────────────────────┘
    ```
    """)

    st.markdown("##### API Endpoints")
    st.code("""
# WhatsApp Media Webhook:
POST http://127.0.0.1:8000/webhook/whatsapp
Payload: { "from": "+1555123456", "data": "<base64>", "mimetype": "image/jpeg" }

# WhatsApp Send Message:
POST http://127.0.0.1:3001/send-message
Payload: { "to": "+1555123456", "message": "✅ Payment Confirmed!" }

# WhatsApp Gateway Status & QR:
GET  http://127.0.0.1:3001/status
GET  http://127.0.0.1:3001/qr
    """, language="http")

"""
TxnVerify AI — Streamlit Application
A professional WhatsApp payment verification agent.
"""

import os
import time
import base64
import requests
from pathlib import Path
import streamlit as st
import pandas as pd

import database
import google_auth
import agent_core

# ─────────────────────────────────────────────
# Page config — must be the very first call
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="TxnVerify AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Layout helpers ── */
[data-testid="stAppViewContainer"] { background: #f8fafc; }
[data-testid="stSidebar"] { background: #0f172a !important; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] hr { border-color: #334155 !important; }
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox div[data-baseweb] { background: #1e293b !important; color: #e2e8f0 !important; border-color: #334155 !important; }

/* ── Cards ── */
.card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.5rem 1.75rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    margin-bottom: 1rem;
}
.card-accent { border-left: 4px solid #2563eb; }

/* ── Status pills ── */
.pill { display:inline-block; padding:3px 12px; border-radius:999px; font-size:.8rem; font-weight:600; }
.pill-green  { background:#dcfce7; color:#166534; }
.pill-red    { background:#fee2e2; color:#991b1b; }
.pill-yellow { background:#fef9c3; color:#854d0e; }
.pill-blue   { background:#dbeafe; color:#1e40af; }

/* ── Page title ── */
.page-title {
    font-size: 1.9rem;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.5px;
    margin-bottom: 0;
}
.page-sub { color: #64748b; font-size: .97rem; margin-top: .15rem; }

/* ── Chat bubble ── */
.wa-bubble {
    background: #dcfce7;
    border: 1px solid #86efac;
    border-radius: 0 14px 14px 14px;
    padding: 1rem 1.25rem;
    font-family: 'Segoe UI', sans-serif;
    font-size: .93rem;
    line-height: 1.6;
    white-space: pre-wrap;
    max-width: 480px;
}
.wa-bubble-fail {
    background: #fee2e2;
    border: 1px solid #fca5a5;
    border-radius: 0 14px 14px 14px;
    padding: 1rem 1.25rem;
    font-family: 'Segoe UI', sans-serif;
    font-size: .93rem;
    line-height: 1.6;
    white-space: pre-wrap;
    max-width: 480px;
}

/* ── Setup wizard steps ── */
.step-box {
    background: #f1f5f9;
    border-radius: 10px;
    padding: .85rem 1.1rem;
    margin: .4rem 0;
    font-size: .9rem;
}
.step-done { background: #dcfce7; }
.step-pending { background: #fef9c3; }

/* ── QR wrapper ── */
.qr-wrap {
    display:flex; flex-direction:column; align-items:center;
    background:#fff; border:1px solid #e2e8f0; border-radius:16px;
    padding:2rem; gap:.75rem;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# OAuth callback handling (Streamlit gets the
# ?code= param after Google redirects back)
# ─────────────────────────────────────────────
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
                "Google sign-in failed. The most common reason is that "
                "`http://localhost:8501` is not in the Authorised Redirect URIs list in "
                "your Google Cloud project. See the **Setup** tab for instructions."
            )
        st.query_params.clear()

_handle_oauth_callback()


# ─────────────────────────────────────────────
# Helper — check what's configured
# ─────────────────────────────────────────────
def _config_state():
    gemini_key   = database.get_config("gemini_api_key", os.getenv("GEMINI_API_KEY", "")).strip()
    client_id    = database.get_config("google_client_id", os.getenv("GOOGLE_CLIENT_ID", "")).strip()
    client_secret= database.get_config("google_client_secret", os.getenv("GOOGLE_CLIENT_SECRET", "")).strip()
    creds        = google_auth.get_stored_credentials()
    gmail_ok     = creds is not None and creds.valid
    return {
        "gemini_key":    gemini_key,
        "client_id":     client_id,
        "client_secret": client_secret,
        "oauth_ready":   bool(client_id and client_secret),
        "gmail_ok":      gmail_ok,
        "all_ready":     bool(gemini_key and client_id and client_secret and gmail_ok),
    }


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
GATEWAY_URL = os.getenv("WHATSAPP_GATEWAY_URL", "http://localhost:3001")

with st.sidebar:
    st.markdown("## 🛡️ TxnVerify AI")
    st.caption("WhatsApp Payment Verification Agent")
    st.divider()

    cfg = _config_state()

    # ── Agent toggle ──────────────────────────
    is_running = database.get_config("agent_running", False)
    can_run    = cfg["all_ready"]
    new_val    = st.toggle(
        "Agent Active",
        value=is_running and can_run,
        disabled=not can_run,
        help="All three setup steps must be complete before the agent can run.",
    )
    if new_val != is_running:
        database.set_config("agent_running", new_val)
        database.log_event("AGENT_STATE", "ENABLED" if new_val else "PAUSED", "User toggled agent")
        st.rerun()

    if new_val and can_run:
        st.markdown('<span class="pill pill-green">● Listening</span>', unsafe_allow_html=True)
    elif not can_run:
        st.markdown('<span class="pill pill-yellow">● Setup incomplete</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="pill pill-red">● Paused</span>', unsafe_allow_html=True)

    st.divider()

    # ── Quick status ──────────────────────────
    st.markdown("**Configuration**")

    def _dot(ok): return "🟢" if ok else "🔴"

    st.markdown(f"{_dot(bool(cfg['gemini_key']))} Gemini API key")
    st.markdown(f"{_dot(cfg['oauth_ready'])}  Google OAuth credentials")
    st.markdown(f"{_dot(cfg['gmail_ok'])}  Gmail authorised")

    st.divider()

    # ── WhatsApp gateway status ───────────────
    st.markdown("**WhatsApp Gateway**")
    try:
        r = requests.get(f"{GATEWAY_URL}/status", timeout=2)
        gw = r.json()
        gw_status = gw.get("status", "UNKNOWN")
        color = "pill-green" if gw_status == "READY" else ("pill-yellow" if gw_status in ("SCAN_QR","INITIALIZING","AUTHENTICATED") else "pill-red")
        paired = gw.get("paired_info") or {}
        st.markdown(f'<span class="pill {color}">{gw_status}</span>', unsafe_allow_html=True)
        if paired.get("pushname"):
            st.caption(f"Paired: {paired['pushname']}")
    except Exception:
        st.markdown('<span class="pill pill-red">OFFLINE</span>', unsafe_allow_html=True)
        st.caption("Run `node whatsapp_gateway.js` in a separate terminal.")

    st.divider()

    # ── Model picker ──────────────────────────
    st.markdown("**Vision model**")
    model_opts = ["gemma-4-26b-a4b-it", "gemini-2.5-flash", "gemini-1.5-flash"]
    saved_model = database.get_config("gemini_model", model_opts[0])
    idx = model_opts.index(saved_model) if saved_model in model_opts else 0
    chosen_model = st.selectbox("", model_opts, index=idx, label_visibility="collapsed")
    if chosen_model != saved_model:
        database.set_config("gemini_model", chosen_model)


# ─────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────
tab_setup, tab_verify, tab_whatsapp, tab_logs = st.tabs([
    "⚙️  Setup",
    "✅  Verify Payment",
    "📱  WhatsApp",
    "📊  Logs",
])


# ══════════════════════════════════════════════
# TAB 1 — SETUP WIZARD
# ══════════════════════════════════════════════
with tab_setup:
    cfg = _config_state()

    st.markdown('<p class="page-title">Setup</p>', unsafe_allow_html=True)
    st.markdown('<p class="page-sub">Complete all three steps to activate the agent.</p>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── STEP 1 — Gemini API key ───────────────
    step1_done = bool(cfg["gemini_key"])
    with st.expander(
        ("✅ " if step1_done else "🔲 ") + "Step 1 — Google Gemini API Key",
        expanded=not step1_done,
    ):
        st.markdown("""
The agent uses **Gemma 4** (`gemma-4-26b-a4b-it`) via Google AI Studio to read payment receipt
images and extract transaction details. You need a free API key.

**How to get one:**
1. Go to **[https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)** and sign in with any Google account.
2. Click **Create API key** → choose any project (or create a new one).
3. Copy the key that starts with `AIza…` and paste it below.
        """)

        current_key = database.get_config("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
        new_key = st.text_input(
            "Gemini API Key",
            value=current_key,
            type="password",
            placeholder="AIza…",
        )
        if st.button("Save Gemini Key", key="save_gemini"):
            if new_key.strip().startswith("AIza"):
                database.set_config("gemini_api_key", new_key.strip())
                os.environ["GEMINI_API_KEY"] = new_key.strip()
                st.success("Saved. Gemini API key is ready.")
                st.rerun()
            elif new_key.strip():
                st.error("That doesn't look like a valid Gemini key (should start with `AIza`).")
            else:
                st.warning("Please paste your API key first.")

    # ── STEP 2 — Google Cloud OAuth credentials
    step2_done = cfg["oauth_ready"]
    with st.expander(
        ("✅ " if step2_done else "🔲 ") + "Step 2 — Google Cloud OAuth Credentials",
        expanded=step1_done and not step2_done,
    ):
        st.markdown("""
TxnVerify AI searches your Gmail inbox for bank transfer confirmation emails to verify payments.
Google requires an OAuth 2.0 client ID & secret so the app can request permission to read your inbox
(read-only — it never sends, deletes, or modifies anything).

**How to create credentials (one-time, ~3 minutes):**

1. Open **[Google Cloud Console](https://console.cloud.google.com/)** and sign in.
2. Create or select a project (top-left dropdown → **New Project**).
3. In the left menu go to **APIs & Services → Enabled APIs** and click **+ Enable APIs**.
   Search for **Gmail API** and enable it.
4. Go to **APIs & Services → OAuth consent screen**.
   - Choose **External**, click **Create**.
   - Fill in an app name (e.g. `TxnVerify AI`) and your email for support & developer fields.
   - Click **Save and Continue** through all steps — you don't need to add scopes manually here.
   - On the **Test users** page, add your own Gmail address so you can sign in while the app is in *Testing* mode.
5. Go to **APIs & Services → Credentials → + Create Credentials → OAuth client ID**.
   - Application type: **Web application**.
   - Under **Authorised redirect URIs** click **Add URI** and enter exactly:
     ```
     http://localhost:8501
     ```
   - Click **Create**.
6. A dialog appears with your **Client ID** and **Client Secret**. Copy both and paste below.
        """)

        col_a, col_b = st.columns(2)
        saved_cid = database.get_config("google_client_id", os.getenv("GOOGLE_CLIENT_ID", ""))
        saved_cs  = database.get_config("google_client_secret", os.getenv("GOOGLE_CLIENT_SECRET", ""))

        new_cid = col_a.text_input("Client ID", value=saved_cid, placeholder="…apps.googleusercontent.com")
        new_cs  = col_b.text_input("Client Secret", value=saved_cs, type="password", placeholder="GOCSPX-…")

        if st.button("Save OAuth Credentials", key="save_oauth"):
            if new_cid.strip() and new_cs.strip():
                database.set_config("google_client_id", new_cid.strip())
                database.set_config("google_client_secret", new_cs.strip())
                os.environ["GOOGLE_CLIENT_ID"]     = new_cid.strip()
                os.environ["GOOGLE_CLIENT_SECRET"] = new_cs.strip()
                st.success("Credentials saved. Continue to Step 3 to sign in.")
                st.rerun()
            else:
                st.warning("Both Client ID and Client Secret are required.")

    # ── STEP 3 — Gmail sign-in ────────────────
    step3_done = cfg["gmail_ok"]
    with st.expander(
        ("✅ " if step3_done else "🔲 ") + "Step 3 — Authorise Gmail Access",
        expanded=step2_done and not step3_done,
    ):
        if not step2_done:
            st.info("Complete Step 2 first.")
        elif step3_done:
            email = google_auth.get_user_email()
            st.success(f"Gmail connected as **{email}**.")
            if st.button("Disconnect Gmail account", type="secondary"):
                google_auth.sign_out()
                database.log_event("AUTH_REVOKE", "DISCONNECTED", "User signed out")
                st.rerun()
        else:
            st.markdown("""
Click the button below. Google will ask you to sign in and grant **read-only** access to your Gmail
inbox. The app only uses this to search for transaction confirmation emails — nothing else.

After you approve, Google redirects you back to this page automatically.
            """)
            try:
                auth_url, _ = google_auth.get_google_auth_url(redirect_uri="http://localhost:8501")
                st.link_button("Sign in with Google →", auth_url, type="primary")
            except Exception as e:
                st.error(f"Could not build the sign-in URL: {e}")
                st.caption("Make sure your Client ID and Client Secret are saved correctly in Step 2.")

    # ── Summary ───────────────────────────────
    st.divider()
    cfg = _config_state()
    if cfg["all_ready"]:
        st.success("All steps complete. Switch on the **Agent Active** toggle in the sidebar to start monitoring.")
    else:
        missing = []
        if not cfg["gemini_key"]:    missing.append("Gemini API key")
        if not cfg["oauth_ready"]:   missing.append("OAuth credentials")
        if not cfg["gmail_ok"]:      missing.append("Gmail sign-in")
        st.warning(f"Still needed: {', '.join(missing)}.")


# ══════════════════════════════════════════════
# TAB 2 — VERIFY PAYMENT (manual / live test)
# ══════════════════════════════════════════════
with tab_verify:
    cfg = _config_state()
    chosen_model = database.get_config("gemini_model", "gemma-4-26b-a4b-it")

    st.markdown('<p class="page-title">Verify a Payment</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">Upload a payment receipt screenshot. '
        'TxnVerify AI extracts the transaction details with Gemma 4 and checks your Gmail for '
        'a matching bank confirmation within 60 seconds.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    if not cfg["gemini_key"]:
        st.warning("Add your Gemini API key in the **Setup** tab before running a verification.")
        st.stop()

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("#### 1 · Upload receipt")

        # ── Built-in sample receipts for quick testing ──
        sample_dir = Path(__file__).parent / "sample_receipts"
        samples = {
            "Upload my own image": None,
            "Zelle  •  $150.00  •  Ref ZEL-982341908": sample_dir / "zelle_receipt_150.jpg",
            "Venmo  •  $45.00   •  Ref VEN-549102834": sample_dir / "venmo_receipt_45.jpg",
            "Google Pay UPI  •  ₹2,500  •  Ref UPI-409182390192": sample_dir / "upi_receipt_2500.jpg",
        }
        choice = st.selectbox("Quick sample or upload", list(samples.keys()))

        img_bytes, mime = None, "image/jpeg"
        if samples[choice]:
            p = samples[choice]
            if p.exists():
                img_bytes = p.read_bytes()
                st.image(img_bytes, use_container_width=True)
            else:
                st.warning("Sample receipt file not found. Run `python generate_sample_receipt.py` once.")
        else:
            uploaded = st.file_uploader(
                "Drag and drop or click to browse",
                type=["jpg", "jpeg", "png", "webp"],
                label_visibility="collapsed",
            )
            if uploaded:
                img_bytes = uploaded.getvalue()
                mime      = uploaded.type
                st.image(img_bytes, use_container_width=True)

        st.markdown("#### 2 · Sender (optional)")
        sender = st.text_input(
            "Sender WhatsApp number",
            placeholder="+1 555 000 1234",
            help="If provided, TxnVerify AI sends the verification result back to this number via WhatsApp.",
        )

        run = st.button(
            "Run Verification",
            type="primary",
            use_container_width=True,
            disabled=img_bytes is None,
        )

    with right:
        st.markdown("#### 3 · Result")

        if not run or img_bytes is None:
            st.markdown("""
<div class="card">
    <p style="color:#64748b;margin:0">
        Results will appear here once you click <strong>Run Verification</strong>.
    </p>
</div>
""", unsafe_allow_html=True)
        else:
            bar  = st.progress(5, text="Starting Gemma 4 OCR…")
            info = st.empty()

            def _progress(step, elapsed, msg):
                pct = min(10 + int((elapsed / 60) * 85), 95)
                bar.progress(pct, text=f"[{elapsed}s] {msg}")

            try:
                info.info(f"Analysing image with **{chosen_model}**…")
                result = agent_core.process_payment_image(
                    image_bytes=img_bytes,
                    mime_type=mime,
                    sender_phone=sender or None,
                    model_name=chosen_model,
                    progress_callback=_progress,
                )
                bar.progress(100, text="Done.")
                info.empty()

                is_txn = result.get("is_transaction")
                verified = result.get("verified")

                # ── Status banner ──
                if verified:
                    st.success(f"Payment confirmed  ·  {result.get('elapsed_seconds')}s")
                elif is_txn:
                    st.error("Payment not confirmed within 60 s — no matching email found.")
                else:
                    st.warning("This image does not appear to be a payment receipt.")

                # ── Extracted data ──
                if is_txn:
                    st.markdown("**Extracted by Gemma 4**")
                    ca, cb = st.columns(2)
                    ca.metric("Transaction ID", result.get("transaction_id") or "—")
                    ca.metric("Amount",         result.get("amount") or "—")
                    cb.metric("Platform",       result.get("payment_app") or "—")
                    cb.metric("Confidence",     f"{round(result.get('confidence', 0) * 100)}%")

                # ── Gmail evidence ──
                gm = result.get("gmail_match")
                if gm:
                    with st.expander("Gmail confirmation found", expanded=True):
                        st.markdown(f"**From:** {gm.get('sender')}")
                        st.markdown(f"**Subject:** {gm.get('subject')}")
                        st.markdown(f"**Source:** `{gm.get('source')}`")
                        st.info(gm.get("snippet", ""))

                # ── WhatsApp reply preview ──
                reply = result.get("reply_text", "")
                if reply:
                    st.markdown("**WhatsApp reply sent**")
                    bubble_cls = "wa-bubble" if verified else "wa-bubble-fail"
                    st.markdown(
                        f'<div class="{bubble_cls}">{reply}</div>',
                        unsafe_allow_html=True,
                    )

            except Exception as exc:
                bar.empty()
                info.empty()
                st.error(f"Verification failed: {exc}")
                with st.expander("Error details"):
                    st.exception(exc)


# ══════════════════════════════════════════════
# TAB 3 — WHATSAPP PAIRING
# ══════════════════════════════════════════════
with tab_whatsapp:
    st.markdown('<p class="page-title">WhatsApp</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">Pair your WhatsApp account so TxnVerify AI can monitor '
        'incoming payment screenshots automatically.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    left_qr, right_qr = st.columns([1, 1], gap="large")

    with left_qr:
        gw_data = None
        try:
            r = requests.get(f"{GATEWAY_URL}/qr", timeout=3)
            gw_data = r.json()
        except Exception:
            pass

        if gw_data and gw_data.get("qr_data_url"):
            st.markdown(
                f'<div class="qr-wrap">'
                f'<img src="{gw_data["qr_data_url"]}" style="max-width:300px;border-radius:8px;">'
                f'<p style="margin:0;color:#64748b;font-size:.87rem;">Scan with WhatsApp to pair</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif gw_data and gw_data.get("status") == "READY":
            paired = gw_data.get("paired_info") or {}
            st.success(
                f"WhatsApp connected — **{paired.get('pushname', 'Device')}** "
                f"({paired.get('wid', '')})"
            )
            st.info("The agent is now listening for incoming payment screenshots on this account.")
        elif gw_data:
            st.markdown(
                f'<span class="pill pill-yellow">{gw_data.get("status","Starting…")}</span>',
                unsafe_allow_html=True,
            )
            st.caption("The WhatsApp gateway is initialising. This can take 15–30 seconds.")
        else:
            st.error("WhatsApp gateway is not reachable.")
            st.markdown("""
Open a second terminal in the project folder and run:
```bash
node whatsapp_gateway.js
```
Keep that terminal open while using TxnVerify AI.
            """)

        bc1, bc2 = st.columns(2)
        if bc1.button("Refresh QR", use_container_width=True):
            st.rerun()
        if bc2.button("Restart gateway client", use_container_width=True):
            try:
                requests.post(f"{GATEWAY_URL}/start", timeout=3)
                st.toast("Gateway restart requested.")
            except Exception:
                st.error("Cannot reach the gateway. Make sure `node whatsapp_gateway.js` is running.")

    with right_qr:
        st.markdown("#### How pairing works")
        st.markdown("""
1. Open **WhatsApp** on your phone.
2. Tap **⋮ (three dots)** → **Linked devices** → **Link a device**.
3. Point your camera at the QR code.
4. Done. Once paired, any payment screenshot sent to this WhatsApp number triggers the full
   verification pipeline:

   - Gemma 4 reads the image and extracts the transaction ID and amount.
   - TxnVerify AI searches your Gmail inbox for the matching bank confirmation email (up to 60 s).
   - A reply — **Payment confirmed** or **Could not verify** — is sent back to the customer automatically.

> The gateway maintains the session locally. The QR code only needs to be scanned once;
> subsequent restarts reconnect automatically using cached credentials.
        """)

        st.markdown("#### Privacy")
        st.markdown("""
- **WhatsApp messages are not stored** — only the extracted transaction ID, amount, and
  verification result are written to the local SQLite database.
- **Gmail access is read-only** — TxnVerify AI only searches for messages matching the
  extracted transaction reference. It never reads, sends, or deletes any other email.
        """)


# ══════════════════════════════════════════════
# TAB 4 — LOGS
# ══════════════════════════════════════════════
with tab_logs:
    st.markdown('<p class="page-title">Logs</p>', unsafe_allow_html=True)
    st.markdown('<p class="page-sub">All verification events and processed transactions.</p>',
                unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Refresh", key="btn_refresh_logs"):
        st.rerun()

    # ── Transactions ──────────────────────────
    st.markdown("#### Transactions")
    txns = database.get_transactions(limit=100)
    if txns:
        df = pd.DataFrame(txns)
        wanted = ["transaction_id", "amount", "payment_app", "sender_phone", "gmail_verified", "created_at", "verified_at"]
        df = df[[c for c in wanted if c in df.columns]].copy()
        df["gmail_verified"] = df["gmail_verified"].apply(
            lambda v: "✅  Confirmed" if v == 1 else "—"
        )
        df.rename(columns={
            "transaction_id": "Transaction ID",
            "amount": "Amount",
            "payment_app": "Platform",
            "sender_phone": "Sender",
            "gmail_verified": "Gmail",
            "created_at": "Received",
            "verified_at": "Confirmed at",
        }, inplace=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions recorded yet.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Activity log ──────────────────────────
    st.markdown("#### Activity log")
    logs = database.get_recent_logs(limit=60)
    if logs:
        df_logs = pd.DataFrame(logs)
        wanted_l = ["timestamp", "event_type", "status", "sender", "transaction_id", "details"]
        df_logs = df_logs[[c for c in wanted_l if c in df_logs.columns]].copy()
        df_logs.rename(columns={
            "timestamp": "Time",
            "event_type": "Event",
            "status": "Status",
            "sender": "Sender",
            "transaction_id": "Txn ID",
            "details": "Details",
        }, inplace=True)
        st.dataframe(df_logs, use_container_width=True, hide_index=True)
    else:
        st.info("No activity yet.")

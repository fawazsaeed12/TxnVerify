# 🛡️ TxnVerify AI — Autonomous WhatsApp Payment Verification Agent

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg?logo=streamlit)](https://streamlit.io)
[![Gemma 4](https://img.shields.io/badge/Reasoning-Gemma%204%20(26b)-orange.svg)](https://ai.google.dev)
[![Gemini 3.8 Flash](https://img.shields.io/badge/Vision%20OCR-Gemini%203.8%20Flash-4285F4.svg?logo=google)](https://aistudio.google.com)
[![Node.js](https://img.shields.io/badge/Gateway-Node.js%20%7C%20whatsapp--web.js-green.svg?logo=nodedotjs)](https://nodejs.org)

> **Eliminating Fake Payment Screenshots for Merchants & Creators.**  
> Real-time payment verification combining **Gemini 3.8 Flash** visual OCR, **Google Gmail API** bank polling, and **Gemma 4 (`gemma-4-26b-a4b-it`)** cross-document semantic reconciliation over WhatsApp.

---

## 🎯 The Problem

Merchants, freelancers, and online sellers lose thousands to **fake payment screenshots** (generated via spoof apps, edited templates, or forged slips). Sellers often ship goods believing a customer's WhatsApp screenshot without manually logging into their bank or waiting for delayed SMS alerts.

Even worse, local digital wallets (like **NayaPay**, **SadaPay**, **Easypaisa**, **Venmo**, or **Cash App**) display **internal wallet transaction hashes** on the customer's receipt, while the merchant's destination bank issues a completely different **interbank settlement reference number** (e.g., Raast, IMPS, ACH, Zelle). A simple database ID search returns zero matches.

---

## 💡 The Solution: 2-Stage Autonomous Verification

**TxnVerify AI** provides a seamless, zero-human-touch verification pipeline:

1. **Stage 1 — Multimodal Vision OCR (`Gemini 3.8 Flash`)**:  
   Intercepts incoming WhatsApp screenshots and extracts all receipt metadata: amount, currency, sender, recipient account suffix, destination bank, payment channel, and timestamp.
2. **Stage 2 — Multi-Faceted Bank Discovery (`Gmail API`)**:  
   Queries the merchant's connected Gmail inbox for candidate credit notifications using fuzzy parameter matching (amount, account last-4 digits, bank title, and time proximity).
3. **Stage 3 — Cross-Document Semantic Reconciliation (`Gemma 4`)**:  
   The core fraud-detection engine powered by **`gemma-4-26b-a4b-it`** reconciles the customer's screenshot data against the official bank alert, authenticates the fund deposit, and retrieves the true bank reference ID.
4. **Stage 4 — Instant Automated WhatsApp Confirmation**:  
   Sends an authenticated reply back to the customer with the official bank reference number and audit breakdown.

---

## 🏗️ System Architecture

```text
 ┌────────────────────────────────────────────────────────┐
 │                   Customer WhatsApp                    │
 │         (Sends payment receipt / transfer slip)        │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │           WhatsApp Gateway Service (:3001)             │
 │        Node.js + Express + whatsapp-web.js             │
 │  • Puppeteer headless browser with encrypted media fix │
 │  • Filters direct payment DMs vs group chatter         │
 └───────────────────────────┬────────────────────────────┘
                             │ HTTP POST (Base64 Image Payload)
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │            TxnVerify AI Server (:8000)                 │
 │                  FastAPI Backend                       │
 └───────────────────────────┬────────────────────────────┘
                             │
       ┌─────────────────────┴─────────────────────┐
       ▼                                           ▼
┌─────────────────────────────┐     ┌─────────────────────────────┐
│  Stage 1: Vision Scanner    │     │  Stage 2: Candidate Search  │
│     Gemini 3.8 Flash        │     │  Gmail API (OAuth 2.0 Web)  │
│                             │     │                             │
│ • Amount: "Rs. 100"         │     │ • Query by amount & suffix  │
│ • Bank: "Faysal Bank"       │────►│ • Retreives live bank alert │
│ • Account Last-4: "3206"    │     │   from efbl@faysalbank.com  │
│ • Channel: "Raast"          │     │ • Decodes plain text body   │
└─────────────────────────────┘     └──────────────┬──────────────┘
                                                   │
                                                   ▼
                                    ┌─────────────────────────────┐
                                    │  Stage 3: Reconciliation    │
                                    │     Gemma 4 (26b / 31b)     │
                                    │                             │
                                    │ • Cross-checks image vs msg │
                                    │ • Verifies true fund credit │
                                    │ • Extracts Official Ref:    │
                                    │   `292055049354`            │
                                    └──────────────┬──────────────┘
                                                   │
                                                   ▼
                                    ┌─────────────────────────────┐
                                    │  Stage 4: WhatsApp Reply    │
                                    │  ✅ Payment Confirmed via   │
                                    │     Gemma 4! Ref: 2920...   │
                                    └─────────────────────────────┘
```

---

## 📱 Real-World Verification Example

### Customer WhatsApp Screenshot (NayaPay)
- **Amount:** `Rs. 100`
- **Sender:** `Muhammad Mubashar Saeed`
- **Destination:** `Faysal Bank ••••3206`
- **Channel:** `Raast`
- **Internal Receipt Hash:** `6adb8358199dd61b0c26...`

### Bank Confirmation Email (Faysal Bank)
- **Sender:** `Faysal bank Limited <efbl@faysalbank.com>`
- **Subject:** `RAAST Fund Transfer`
- **Body:** `Your account has been credited via RAAST payment. Amount: PKR 100.00, Account: PK08FAYS******3206, Reference: 292055049354`

### Automated WhatsApp Output (Dispatched in <10s)
```text
✅ *Payment Confirmed via Gemma 4!*

• *Amount Credited:* Rs. 100
• *Official Bank Ref:* `292055049354`
• *Method/App:* NayaPay
• *Destination:* Faysal Bank (Account ending in 3206)
• *Verified via:* Faysal bank Limited (RAAST Fund Transfer)
• *Audit Summary:* All transaction parameters, including amount, receiver account suffix, sender name, and timestamp, show a perfect match between the receipt and the bank notification.
• *Verification Time:* 9.96s

✨ Your transaction has been reconciled and authenticated against official bank records.
```

---

## 🖥️ Modern Obsidian Control Dashboard

The Streamlit UI (`app.py`) features an **Obsidian glassmorphism theme** organized into three focused tabs:

| Tab | Purpose |
| :--- | :--- |
| **⚙️ Setup & Authentication** | 1-click credential configuration for **Google Gemini API Key** and **Google Cloud OAuth 2.0 Client** (with direct links to enable the Gmail API), plus an **Offline Sandbox Mode** for testing without live credentials. |
| **📱 WhatsApp Gateway** | Live QR code scanner for pairing your WhatsApp Web device, real-time connection status (`READY`, `SCAN_QR`, `DISCONNECTED`), and pairing telemetry. |
| **📜 Real-Time Audit Trail** | Live SQLite history recording all processed transactions, customer phone numbers, OCR extracted data, official bank reference numbers, and Gemma 4 reconciliation notes. |

---

## 📂 Repository Layout

```text
TxnVerify/
├── app.py                  # Streamlit Control Dashboard (Obsidian UI)
├── agent_core.py           # 2-Stage Engine: Gemini 3.8 Flash Vision + Gemma 4 Reconciliation
├── google_auth.py          # Google OAuth 2.0 Web flow (PKCE) & Gmail API Client
├── database.py             # SQLite persistence layer (schema, migrations, config, audit logs)
├── webhook_server.py       # FastAPI webhook server receiving media from WhatsApp gateway
├── whatsapp_gateway.js     # Node.js + Express + whatsapp-web.js WhatsApp gateway
├── patch_wwebjs.js         # Puppeteer patch ensuring full high-resolution media downloads
├── run_all.py              # Master supervisor starting FastAPI, Gateway, and Dashboard
├── package.json            # Node.js dependencies
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
└── LICENSE                 # MIT License
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** & **npm**
- A free **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/)

### 2. Installation

Clone the repository:
```bash
git clone https://github.com/fawazsaeed12/TxnVerify.git
cd TxnVerify
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

Install Node.js dependencies & apply WhatsApp Web patch:
```bash
npm install
node patch_wwebjs.js
```

### 3. Launch the Application

Start all services with a single command:
```bash
python run_all.py
```

This automatically orchestrates:
- **FastAPI Webhook Server** on `http://localhost:8000`
- **WhatsApp Web Gateway** on `http://localhost:3001`
- **Streamlit Control Dashboard** on `http://localhost:8501`

Open your browser to: **`http://localhost:8501`**

---

## ⚙️ Initial Configuration (in Streamlit UI)

1. Open **`http://localhost:8501`** and navigate to the **⚙️ Setup & Authentication** tab.
2. **Step 1:** Paste your **Gemini API Key** and click **Save**.
3. **Step 2:** (Optional for live Gmail) Enter your Google Cloud OAuth **Client ID** & **Client Secret**.
   > *Note:* If testing offline or during demos, leave Google OAuth empty and tick **"🧪 Enable Offline Sandbox Inbox"** to use pre-seeded bank notifications.
4. **Step 3:** Switch to the **📱 WhatsApp Gateway** tab, scan the QR code with your WhatsApp app (**Linked Devices ➔ Link a Device**).
5. Send any bank transfer screenshot to the paired WhatsApp number — **TxnVerify AI** will verify the payment and respond instantly!

---

## 🔒 Security & Privacy

- **Read-Only Scopes:** Requests strictly `https://www.googleapis.com/auth/gmail.readonly`. The agent cannot send, modify, or delete emails.
- **PKCE OAuth 2.0:** Implements RFC 7636 Proof Key for Code Exchange to prevent authorization code interception.
- **Local Isolation:** Secrets, tokens, and database records remain strictly on your local machine; `.gitignore` is pre-configured to prevent accidental commits of credentials.
- **In-Memory Media Processing:** Screenshots are processed in memory and never leaked to external public storage.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

# 🛡️ TxnVerify AI: Automated WhatsApp Payment Verification Agent

> **Built for Hackathons** • Powered by **Gemma 4 (`gemma-4-26b-a4b-it`)** & **Gmail API** with **`whatsapp-web.js`**

TxnVerify AI is a production-ready, autonomous WhatsApp verification agent designed for small businesses, online sellers, and event organizers. When customers send screenshots of bank transfers or payment slips via WhatsApp, TxnVerify AI intercepts the image in real time, uses **Gemma 4** for visual OCR and structured parameter extraction, starts a **60-second polling loop** against the merchant's **Gmail inbox** via Google OAuth 2.0, and automatically responds back on WhatsApp with **`✅ Payment Confirmed`** or **`❌ Unverified`**.

---

## 🏗️ Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │            Customer WhatsApp           │
                      │       (Sends payment receipt image)    │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │    WhatsApp Gateway Service (:3001)    │
                      │  Node.js + Express + whatsapp-web.js   │
                      │  • Pair phone via live QR code         │
                      │  • Intercepts media messages           │
                      └───────────────────┬────────────────────┘
                                          │ HTTP POST (Base64 Image)
                                          ▼
                      ┌────────────────────────────────────────┐
                      │       TxnVerify AI Engine (:8000)      │
                      │             FastAPI Backend            │
                      └─────────────┬──────────────────────────┘
                                    │
            ┌───────────────────────┴───────────────────────┐
            ▼                                               ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│       Gemma 4 Vision OCR      │               │     60s Gmail Polling Loop    │
│    `gemma-4-26b-a4b-it`       │               │    Google OAuth 2.0 Web Auth  │
│                               │               │                               │
│ • Extracts structured JSON:   │               │ • Polls `users.messages.list` │
│   - `is_transaction`: bool    │               │   with `q=transaction_id`     │
│   - `transaction_id`: str     │ ────────────► │ • Inspects headers:           │
│   - `amount`: str             │               │   Subject, Sender, Snippet    │
│   - `payment_app`: str        │               │ • Confirms credit match       │
└───────────────────────────────┘               └───────────────┬───────────────┘
                                                                │
                                                                ▼
                                                ┌───────────────────────────────┐
                                                │   Automated WhatsApp Reply    │
                                                │   ✅ Payment Confirmed / ❌   │
                                                └───────────────────────────────┘
```

---

## ✨ Key Features

1. **Gemma 4 Visual Extraction (`gemma-4-26b-a4b-it`):**
   - High-precision OCR tailored for mobile transaction screenshots (Zelle, Venmo, Cash App, PayPal, Apple Pay, UPI / Google Pay, Chase, Bank of America, etc.).
   - Returns structured JSON specifying whether the image is a valid receipt, the unique reference/UTR/transaction ID, and the transferred amount.

2. **Google OAuth 2.0 Direct Gmail Integration:**
   - 1-click **"Sign in with Google"** web authorization flow requesting `gmail.readonly` scope.
   - End users do not need to configure raw JSON files or manually paste access tokens.

3. **60-Second Real-Time Inbox Polling:**
   - Immediately upon extracting the transaction reference, queries `users.messages.list(userId='me', q=transaction_id)` every 5 seconds for up to 60 seconds to match real bank notification emails.

4. **Interactive Streamlit Control Dashboard (`app.py`):**
   - **Start / Stop Agent** toggle switch with real-time status indication.
   - Live **WhatsApp QR Code** pairing viewer.
   - **Judge Test Panel:** Drag-and-drop receipt tester with instant visual extraction cards, Gmail match preview, and WhatsApp chat bubble simulator.
   - **Real-Time Audit Trail:** SQLite persistence tracking all processed transactions, confidence ratings, and timestamps.

5. **Sandbox Demo Mode for Judges:**
   - Includes realistic pre-generated sample receipts (Zelle, Venmo, UPI) and seeded mock confirmation emails so judges can evaluate the entire end-to-end pipeline in seconds without needing a live bank transaction.

---

## 📁 Codebase Structure

```
hackathon/
├── app.py                      # Streamlit Control Dashboard & Judge Test Panel
├── agent_core.py               # Gemma 4 Visual OCR & 60-Second Gmail Polling Engine
├── google_auth.py              # Google OAuth 2.0 Web Flow & Gmail API Client
├── database.py                 # SQLite persistence for logs, transactions & settings
├── webhook_server.py           # FastAPI server receiving WhatsApp Gateway media webhooks
├── whatsapp_gateway.js         # Node.js + Express + whatsapp-web.js gateway
├── generate_sample_receipt.py  # Generates test receipts & seeds mock inbox for judges
├── run_all.py                  # Process orchestrator (launches all 3 services)
├── package.json                # Node.js dependencies
├── requirements.txt            # Python dependencies
├── .env.example                # Configuration template
└── sample_receipts/            # Pre-generated sample receipts for live demo
```

---

## 🚀 Quickstart Guide

### 1. Install Dependencies

**Python Dependencies:**
```bash
pip install -r requirements.txt
```

**Node.js Dependencies:**
```bash
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env` (or enter your keys directly in the Streamlit UI):
```bash
cp .env.example .env
```
Add your **Google Gemini API Key** from [Google AI Studio](https://aistudio.google.com/).

### 3. Generate Sample Receipts & Seed Mock Inbox
```bash
python generate_sample_receipt.py
```

### 4. Launch the Full Stack

Run the unified orchestrator:
```bash
python run_all.py
```

Or start the individual services in separate terminals:
- **Streamlit Dashboard:** `streamlit run app.py --server.port 8501`
- **FastAPI Webhook Server:** `python webhook_server.py`
- **WhatsApp Gateway:** `node whatsapp_gateway.js`

Open your browser to: **`http://localhost:8501`**

---


## 🔒 Security & Privacy

- **Minimal Gmail Scope:** TxnVerify AI requests strictly `https://www.googleapis.com/auth/gmail.readonly`. It never requests write or send permissions.
- **Ephemerality:** Screenshots are processed in-memory and raw tokens are isolated on the user's local instance.
- **No Hardcoded Secrets:** Environment variables and SQLite secure storage ensure keys are never exposed in commits.

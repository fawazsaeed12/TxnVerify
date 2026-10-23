"""
TxnVerify AI - Core AI Engine (Gemma 4 Visual OCR & Gmail Verification)
Extracts structured transaction information from payment screenshots using Gemma 4 (gemma-4-26b-a4b-it),
polls Gmail for 60 seconds to find bank confirmation emails, and dispatches WhatsApp replies.
"""

import os
import time
import json
import re
import logging
from typing import Dict, Any, Optional, Tuple, Callable
from io import BytesIO
from PIL import Image
import requests

import database
import google_auth

logger = logging.getLogger("txnverify.agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Default model per specification
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")
WHATSAPP_GATEWAY_URL = os.getenv("WHATSAPP_GATEWAY_URL", "http://localhost:3001")

EXTRACTION_SYSTEM_PROMPT = """You are TxnVerify AI, an expert banking and payment verification OCR engine.
Analyze the provided image of a payment receipt, bank transfer, or transaction confirmation screenshot.
Extract the transaction details into clean JSON.

You must return a valid JSON object with EXACTLY these keys:
{
  "is_transaction": boolean,       // true if this image is a payment receipt/transfer confirmation
  "transaction_id": string or null, // alphanumeric transaction ref/ID (e.g. UTR, Ref #, Txn ID, Order ID)
  "amount": string or null,         // currency symbol and amount (e.g. "$150.00", "₹500.00", "€45.50")
  "payment_app": string or null,    // detected platform (e.g., "Zelle", "Venmo", "PayPal", "CashApp", "GPay", "Chase", "UPI")
  "sender_name": string or null,    // sender or payer name if visible
  "receiver_name": string or null,  // recipient or payee name if visible
  "confidence": number              // float from 0.0 to 1.0 indicating confidence in extraction
}

Strict requirements:
1. If the image is not a payment receipt or transaction screenshot, set "is_transaction": false and others to null.
2. Be extremely precise with the "transaction_id". Remove surrounding labels like "Ref:" or "Txn ID:" and extract only the exact alphanumeric reference identifier.
3. Output RAW JSON ONLY. Do not enclose in markdown ticks if possible, or output inside ```json ```.
"""


def get_gemini_api_key() -> str:
    """Retrieve Gemini API key from environment, config, or database."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        key = database.get_config("gemini_api_key")
    return key or ""


def extract_with_google_genai(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Extract structured payment info from an image buffer using Google GenAI SDK.
    Supports gemma-4-26b-a4b-it.
    """
    key = api_key or get_gemini_api_key()
    if not key:
        raise ValueError("Missing Gemini API Key. Please provide a valid key in the dashboard or .env file.")

    raw_text = ""

    # Primary: try the modern google.genai Client SDK
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)

        part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )

        response = client.models.generate_content(
            model=model_name,
            contents=[part, EXTRACTION_SYSTEM_PROMPT],
        )

        raw_text = response.text or ""

    except Exception as e:
        logger.warning(f"google.genai SDK call failed with model '{model_name}': {e}. Attempting fallback...")
        # Fallback 1: try google.generativeai if available
        try:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=key)

            img = Image.open(BytesIO(image_bytes))
            # Try user model or fallback to gemini-2.5-flash if gemma-4 model alias is not in legacy SDK
            try:
                legacy_model = genai_legacy.GenerativeModel(model_name)
                resp = legacy_model.generate_content([EXTRACTION_SYSTEM_PROMPT, img])
                raw_text = resp.text
            except Exception:
                fallback_model = genai_legacy.GenerativeModel("gemini-1.5-flash")
                resp = fallback_model.generate_content([EXTRACTION_SYSTEM_PROMPT, img])
                raw_text = resp.text
        except Exception as e2:
            logger.error(f"Legacy generativeai fallback also failed: {e2}")
            raise RuntimeError(f"Gemma 4 / Gemini API error: {e}") from e

    # Parse JSON from response
    parsed = parse_ocr_json_response(raw_text)
    return parsed


def parse_ocr_json_response(raw_text: str) -> Dict[str, Any]:
    """Clean and parse JSON from model output."""
    if not raw_text:
        return {"is_transaction": False, "transaction_id": None, "amount": None, "confidence": 0.0}

    # Remove markdown code fences if present
    cleaned = raw_text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(cleaned)
        # Ensure standard keys
        return {
            "is_transaction": bool(data.get("is_transaction", False)),
            "transaction_id": str(data.get("transaction_id")).strip() if data.get("transaction_id") else None,
            "amount": str(data.get("amount")).strip() if data.get("amount") else None,
            "payment_app": data.get("payment_app"),
            "sender_name": data.get("sender_name"),
            "receiver_name": data.get("receiver_name"),
            "confidence": float(data.get("confidence", 0.95) if data.get("confidence") is not None else 0.95),
            "raw_text": raw_text
        }
    except Exception as e:
        logger.warning(f"JSON parsing error: {e}. Raw text was: {raw_text[:200]}")
        # Regex fallback for transaction_id and amount
        txn_match = re.search(r'"transaction_id":\s*"([^"]+)"', raw_text, re.IGNORECASE)
        amt_match = re.search(r'"amount":\s*"([^"]+)"', raw_text, re.IGNORECASE)
        is_txn_match = re.search(r'"is_transaction":\s*(true|false)', raw_text, re.IGNORECASE)

        is_txn = is_txn_match.group(1).lower() == "true" if is_txn_match else bool(txn_match)

        return {
            "is_transaction": is_txn,
            "transaction_id": txn_match.group(1) if txn_match else None,
            "amount": amt_match.group(1) if amt_match else None,
            "payment_app": "Detected App",
            "sender_name": None,
            "receiver_name": None,
            "confidence": 0.8 if is_txn else 0.0,
            "raw_text": raw_text
        }


def poll_gmail_for_transaction(
    transaction_id: str,
    timeout_seconds: int = 60,
    poll_interval: int = 5,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Tuple[bool, Optional[Dict[str, Any]], float]:
    """
    Polls Gmail inbox for up to timeout_seconds (default 60s) looking for transaction_id.
    Returns (is_verified, email_details, elapsed_time_seconds).
    """
    start_time = time.time()
    attempt = 0
    logger.info(f"Starting 60s Gmail polling loop for Transaction ID: '{transaction_id}'")

    while (time.time() - start_time) < timeout_seconds:
        attempt += 1
        elapsed = round(time.time() - start_time, 1)

        status_msg = f"Polling Gmail (attempt #{attempt}, {elapsed}s / {timeout_seconds}s) for '{transaction_id}'..."
        logger.info(status_msg)
        if progress_callback:
            progress_callback(attempt, int(elapsed), status_msg)

        match = google_auth.query_gmail_for_transaction(transaction_id)
        if match:
            total_elapsed = round(time.time() - start_time, 2)
            logger.info(f"✅ Match found in Gmail after {total_elapsed}s! Subject: {match.get('subject')}")
            if progress_callback:
                progress_callback(attempt, int(total_elapsed), f"Match confirmed in Gmail ({total_elapsed}s)")
            return True, match, total_elapsed

        time.sleep(poll_interval)

    total_elapsed = round(time.time() - start_time, 2)
    logger.warning(f"❌ Gmail polling timeout reached ({total_elapsed}s). No match found for '{transaction_id}'.")
    return False, None, total_elapsed


def format_whatsapp_reply(
    is_transaction: bool,
    is_verified: bool,
    transaction_id: Optional[str] = None,
    amount: Optional[str] = None,
    payment_app: Optional[str] = None,
    gmail_match: Optional[Dict[str, Any]] = None,
    elapsed_seconds: float = 0.0
) -> str:
    """Generate standardized WhatsApp verification response."""
    if not is_transaction:
        return (
            "⚠️ *TxnVerify AI Notification*\n\n"
            "We received your image, but could not detect a valid payment receipt or transaction reference.\n\n"
            "Please send a clear screenshot showing the *Transaction ID* and *Amount*."
        )

    if is_verified:
        subject = gmail_match.get("subject", "Official Payment Confirmation") if gmail_match else "Bank Alert"
        sender = gmail_match.get("sender", "Bank") if gmail_match else "Bank Notification"
        return (
            "✅ *Payment Confirmed!*\n\n"
            f"• *Transaction ID:* `{transaction_id}`\n"
            f"• *Amount:* {amount or 'N/A'}\n"
            f"• *Method:* {payment_app or 'Direct Transfer'}\n"
            f"• *Verified via:* {sender} ({subject})\n"
            f"• *Response Time:* {elapsed_seconds}s\n\n"
            "Thank you! Your transaction has been automatically authenticated and recorded."
        )
    else:
        return (
            "❌ *Payment Unverified*\n\n"
            f"• *Transaction ID:* `{transaction_id}`\n"
            f"• *Amount:* {amount or 'N/A'}\n"
            f"• *Status:* No matching confirmation email received in Gmail after 60 seconds of monitoring.\n\n"
            "If your bank or wallet delays confirmation emails, please try again in a few moments or contact support."
        )


def send_whatsapp_message(to: str, message: str) -> bool:
    """Send text message back to WhatsApp chat via WhatsApp gateway service."""
    if not to:
        return False
    try:
        response = requests.post(
            f"{WHATSAPP_GATEWAY_URL}/send-message",
            json={"to": to, "message": message},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"Could not forward message to WhatsApp gateway: {e}")
        return False


def process_payment_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    sender_phone: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Any]:
    """
    End-to-end payment processing pipeline:
    1. Gemma 4 Visual OCR extraction
    2. Save transaction to DB
    3. 60-second Gmail inbox polling
    4. Database update
    5. WhatsApp automated reply
    """
    start_time = time.time()

    # Step 1: Gemma 4 Visual OCR
    database.log_event("OCR_START", "PROCESSING", "Analyzing image with Gemma 4", sender=sender_phone)
    if progress_callback:
        progress_callback(0, 0, f"Analyzing receipt with Gemma 4 ({model_name})...")

    ocr_result = extract_with_google_genai(
        image_bytes=image_bytes,
        mime_type=mime_type,
        api_key=api_key,
        model_name=model_name
    )

    is_transaction = ocr_result.get("is_transaction", False)
    txn_id = ocr_result.get("transaction_id")
    amount = ocr_result.get("amount")
    payment_app = ocr_result.get("payment_app")
    confidence = ocr_result.get("confidence", 0.95)

    if not is_transaction or not txn_id:
        reply_text = format_whatsapp_reply(is_transaction=False, is_verified=False)
        database.log_event("OCR_FAILED", "REJECTED", "No transaction ID detected", sender=sender_phone)

        if sender_phone:
            send_whatsapp_message(sender_phone, reply_text)

        return {
            "success": False,
            "is_transaction": False,
            "transaction_id": None,
            "amount": None,
            "ocr_result": ocr_result,
            "verified": False,
            "reply_text": reply_text,
            "elapsed_seconds": round(time.time() - start_time, 2)
        }

    # Step 2: Record in Database
    database.save_transaction(
        transaction_id=txn_id,
        amount=amount,
        sender_phone=sender_phone,
        payment_app=payment_app,
        ocr_confidence=confidence,
        raw_ocr_json=json.dumps(ocr_result)
    )
    database.log_event("OCR_SUCCESS", "EXTRACTED", f"Extracted Txn ID: {txn_id}, Amount: {amount}",
                       sender=sender_phone, transaction_id=txn_id, amount=amount)

    # Step 3: 60-second Gmail Polling Loop
    database.log_event("GMAIL_POLL_START", "POLLING", f"Polling Gmail for 60s for {txn_id}",
                       sender=sender_phone, transaction_id=txn_id)

    is_verified, gmail_match, poll_elapsed = poll_gmail_for_transaction(
        transaction_id=txn_id,
        timeout_seconds=60,
        poll_interval=5,
        progress_callback=progress_callback
    )

    # Step 4: Update Database
    if is_verified and gmail_match:
        database.mark_transaction_verified(
            transaction_id=txn_id,
            gmail_message_id=gmail_match.get("id", ""),
            gmail_subject=gmail_match.get("subject", ""),
            gmail_snippet=gmail_match.get("snippet", "")
        )
        database.log_event("VERIFIED", "SUCCESS", f"Confirmed in Gmail: {gmail_match.get('subject')}",
                           sender=sender_phone, transaction_id=txn_id, amount=amount)
    else:
        database.log_event("UNVERIFIED", "TIMEOUT", "No matching email found within 60s",
                           sender=sender_phone, transaction_id=txn_id, amount=amount)

    # Step 5: Format Reply and Dispatch back to WhatsApp
    reply_text = format_whatsapp_reply(
        is_transaction=True,
        is_verified=is_verified,
        transaction_id=txn_id,
        amount=amount,
        payment_app=payment_app,
        gmail_match=gmail_match,
        elapsed_seconds=poll_elapsed
    )

    if sender_phone:
        sent = send_whatsapp_message(sender_phone, reply_text)
        database.log_event("WHATSAPP_REPLY", "SENT" if sent else "FAILED", f"Dispatched reply to {sender_phone}",
                           sender=sender_phone, transaction_id=txn_id)

    total_time = round(time.time() - start_time, 2)
    return {
        "success": True,
        "is_transaction": True,
        "transaction_id": txn_id,
        "amount": amount,
        "payment_app": payment_app,
        "confidence": confidence,
        "ocr_result": ocr_result,
        "verified": is_verified,
        "gmail_match": gmail_match,
        "reply_text": reply_text,
        "elapsed_seconds": total_time
    }

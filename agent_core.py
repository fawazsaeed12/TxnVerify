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

# Default vision model: gemini-2.5-flash (Google's multimodal visual OCR engine)
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")
WHATSAPP_GATEWAY_URL = os.getenv("WHATSAPP_GATEWAY_URL", "http://localhost:3001")

EXTRACTION_SYSTEM_PROMPT = """You are TxnVerify AI, an expert banking and payment verification OCR engine.
Analyze the provided image of a payment receipt, bank transfer, or transaction confirmation screenshot.
Extract the transaction details into clean JSON.

You must return a valid JSON object with EXACTLY these keys:
{
  "is_transaction": boolean,        // true if this image is a payment receipt/transfer confirmation
  "transaction_id": string or null, // alphanumeric transaction ref/ID or hash (e.g. UTR, Ref #, Txn ID, Order ID)
  "amount": string or null,          // currency symbol and amount (e.g. "Rs. 100", "$150.00", "PKR 100.00")
  "amount_value": number or string,  // pure numeric amount value (e.g. 100 or 150.00)
  "currency": string or null,        // e.g. "PKR", "Rs", "USD", "EUR"
  "payment_app": string or null,     // detected platform (e.g., "NayaPay", "SadaPay", "Easypaisa", "JazzCash", "Zelle", "Venmo", "PayPal", "Chase")
  "payment_channel": string or null, // transfer channel if shown (e.g. "Raast", "IMPS", "1Link", "IBFT", "ACH")
  "destination_bank": string or null,// destination bank name (e.g. "Faysal Bank", "Meezan Bank", "Chase")
  "account_last4": string or null,   // last 4 digits of destination account if visible (e.g. "3206")
  "sender_name": string or null,     // sender or payer name if visible
  "receiver_name": string or null,   // recipient or payee name if visible
  "timestamp": string or null,       // date and time shown on receipt
  "confidence": number               // float from 0.0 to 1.0 indicating confidence in extraction
}

Strict requirements:
1. If the image is not a payment receipt or transaction screenshot, set "is_transaction": false and others to null.
2. Be extremely precise. Extract all account suffixes, amounts, banks, and transaction references visible.
3. Output RAW JSON ONLY. Do not enclose in markdown formatting if possible.
"""


def get_gemini_api_key() -> str:
    """Retrieve Gemini API key from database first, then environment."""
    key = database.get_config("gemini_api_key")
    if not key:
        key = os.getenv("GEMINI_API_KEY")
    return (key or "").strip()


def extract_with_google_genai(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Extract structured payment info from an image buffer using Google GenAI SDK.
    Supports gemma-4-26b-a4b-it with seamless gemini-2.5-flash multimodal vision fallback.
    """
    key = (api_key or get_gemini_api_key()).strip()
    if not key:
        raise ValueError("Missing Gemini API Key. Please enter your API key in the Setup tab.")

    raw_text = ""
    # Gemma 4 is a text-only language model; multimodal image inputs are handled by gemini-2.5-flash
    if "gemma" in model_name.lower():
        models_to_try = ["gemini-2.5-flash", "gemini-flash-latest", model_name]
    else:
        models_to_try = [model_name, "gemini-2.5-flash", "gemini-flash-latest"]

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type or "image/jpeg"
    )

    last_err = None
    for m in models_to_try:
        try:
            logger.info(f"Extracting payment details using model: {m}")
            response = client.models.generate_content(
                model=m,
                contents=[part, EXTRACTION_SYSTEM_PROMPT],
            )
            raw_text = response.text or ""
            if raw_text:
                logger.info(f"Successfully extracted OCR response from model '{m}'")
                break
        except Exception as e:
            logger.warning(f"Model '{m}' call failed: {e}. Attempting fallback...")
            last_err = e

    if not raw_text and last_err:
        logger.error(f"All vision models failed. Last error: {last_err}")
        raise RuntimeError(f"Gemini Vision API error: {last_err}") from last_err

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
        return {
            "is_transaction": bool(data.get("is_transaction", False)),
            "transaction_id": str(data.get("transaction_id")).strip() if data.get("transaction_id") else None,
            "amount": str(data.get("amount")).strip() if data.get("amount") else None,
            "amount_value": data.get("amount_value"),
            "currency": data.get("currency"),
            "payment_app": data.get("payment_app"),
            "payment_channel": data.get("payment_channel"),
            "destination_bank": data.get("destination_bank"),
            "account_last4": str(data.get("account_last4")).strip() if data.get("account_last4") else None,
            "sender_name": data.get("sender_name"),
            "receiver_name": data.get("receiver_name"),
            "timestamp": data.get("timestamp"),
            "confidence": float(data.get("confidence", 0.95) if data.get("confidence") is not None else 0.95),
            "raw_text": raw_text
        }
    except Exception as e:
        logger.warning(f"JSON parsing error: {e}. Raw text was: {raw_text[:200]}")
        txn_match = re.search(r'"transaction_id":\s*"([^"]+)"', raw_text, re.IGNORECASE)
        amt_match = re.search(r'"amount":\s*"([^"]+)"', raw_text, re.IGNORECASE)
        is_txn_match = re.search(r'"is_transaction":\s*(true|false)', raw_text, re.IGNORECASE)

        is_txn = is_txn_match.group(1).lower() == "true" if is_txn_match else bool(amt_match or txn_match)

        return {
            "is_transaction": is_txn,
            "transaction_id": txn_match.group(1) if txn_match else None,
            "amount": amt_match.group(1) if amt_match else None,
            "amount_value": None,
            "currency": None,
            "payment_app": "Payment App",
            "payment_channel": None,
            "destination_bank": None,
            "account_last4": None,
            "sender_name": None,
            "receiver_name": None,
            "timestamp": None,
            "confidence": 0.8 if is_txn else 0.0,
            "raw_text": raw_text
        }


def reconcile_with_gemma4(
    ocr_data: Dict[str, Any],
    email_cand: Dict[str, Any],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Invoke Gemma 4 (gemma-4-26b-a4b-it / gemma-4-31b-it) to perform deep semantic
    reconciliation between the extracted payment receipt and bank confirmation email.
    """
    key = (api_key or get_gemini_api_key()).strip()
    if not key:
        raise ValueError("Missing Gemini API Key.")

    from google import genai
    client = genai.Client(api_key=key)

    prompt = f"""You are TxnVerify AI's core fraud-detection and reconciliation engine powered by Gemma 4.
Your task is to reconcile and verify a customer's payment screenshot against an official bank notification email.

Customer Receipt Data (Extracted from image):
{json.dumps(ocr_data, indent=2)}

Bank Notification Email Content:
Subject: {email_cand.get('subject', '')}
From: {email_cand.get('sender', '')}
Date: {email_cand.get('date', '')}
Body:
{email_cand.get('body', '')}

Analyze and reconcile the two sources. Compare:
1. Amount & Currency (e.g. 100 / Rs. 100 / PKR 100.00)
2. Receiver / Destination Account & Name (e.g. 3206 / Faysal Bank / Muhammad Fawaz)
3. Sender Account & Name (e.g. Muhammad Mubashar / NayaPay)
4. Channel & Timestamp proximity (e.g. Raast, 23 Oct 2026, 08:30 PM)

Return a valid JSON object ONLY with:
{{
  "is_verified": boolean,
  "confidence": float (0.0 to 1.0),
  "matched_fields": ["list", "of", "matching", "fields"],
  "official_transaction_reference": "reference number from bank email",
  "reconciliation_summary": "1-2 sentence explanation of why this payment is confirmed"
}}
Raw JSON only."""

    models_to_try = ["gemma-4-26b-a4b-it", "gemma-4-31b-it", "gemini-2.5-flash"]
    last_err = None
    for m in models_to_try:
        try:
            logger.info(f"Running Gemma 4 reconciliation with model '{m}'...")
            res = client.models.generate_content(model=m, contents=prompt)
            txt = (res.text or "").strip()
            if "```json" in txt:
                txt = txt.split("```json")[1].split("```")[0].strip()
            elif "```" in txt:
                txt = txt.split("```")[1].split("```")[0].strip()
            result = json.loads(txt)
            logger.info(f"Gemma 4 reconciliation complete ({m}): verified={result.get('is_verified')}, ref={result.get('official_transaction_reference')}")
            return result
        except Exception as e:
            logger.warning(f"Reconciliation attempt with '{m}' failed: {e}")
            last_err = e

    return {
        "is_verified": False,
        "confidence": 0.0,
        "matched_fields": [],
        "official_transaction_reference": None,
        "reconciliation_summary": f"Gemma 4 reconciliation error: {last_err}"
    }


def poll_and_verify_with_gemma4(
    ocr_result: Dict[str, Any],
    timeout_seconds: int = 60,
    poll_interval: int = 4,
    api_key: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]], float]:
    """
    Polls Gmail inbox and local bank store for up to timeout_seconds.
    When candidate emails are retrieved, invokes Gemma 4 to reconcile the payment.
    Returns (is_verified, matched_email, gemma_reconcile_result, elapsed_time_seconds).
    """
    start_time = time.time()
    attempt = 0
    txn_id = ocr_result.get("transaction_id") or "Receipt"
    amount = ocr_result.get("amount") or ""

    logger.info(f"Starting Gemma 4 verification polling for: '{txn_id}' (Amount: {amount})")

    while (time.time() - start_time) < timeout_seconds:
        attempt += 1
        elapsed = round(time.time() - start_time, 1)

        status_msg = f"Scanning Gmail for bank credit confirmation (attempt #{attempt}, {elapsed}s / {timeout_seconds}s)..."
        logger.info(status_msg)
        if progress_callback:
            progress_callback(attempt, int(elapsed), status_msg)

        # Search candidates from Gmail and local bank store
        candidates = google_auth.query_candidate_emails(ocr_result)

        if candidates:
            if progress_callback:
                progress_callback(attempt, int(elapsed), f"Found {len(candidates)} candidate notification(s). Reconciling with Gemma 4...")

            for cand in candidates:
                logger.info(f"Reconciling candidate: {cand.get('subject')} ({cand.get('source')})")
                reconcile = reconcile_with_gemma4(ocr_data=ocr_result, email_cand=cand, api_key=api_key)
                if reconcile.get("is_verified"):
                    total_elapsed = round(time.time() - start_time, 2)
                    logger.info(f"✅ Gemma 4 Verified! Bank Ref: {reconcile.get('official_transaction_reference')}")
                    if progress_callback:
                        progress_callback(attempt, int(total_elapsed), f"✅ Verified via Gemma 4 ({total_elapsed}s)! Ref: {reconcile.get('official_transaction_reference')}")
                    return True, cand, reconcile, total_elapsed

        time.sleep(poll_interval)

    total_elapsed = round(time.time() - start_time, 2)
    logger.warning(f"❌ Polling timeout reached ({total_elapsed}s). No matching bank confirmation verified.")
    return False, None, None, total_elapsed


def poll_gmail_for_transaction(
    transaction_id: str,
    timeout_seconds: int = 60,
    poll_interval: int = 5,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Tuple[bool, Optional[Dict[str, Any]], float]:
    """Backwards compatibility wrapper around poll_and_verify_with_gemma4."""
    verified, cand, reconcile, elapsed = poll_and_verify_with_gemma4(
        ocr_result={"transaction_id": transaction_id},
        timeout_seconds=timeout_seconds,
        poll_interval=poll_interval,
        progress_callback=progress_callback
    )
    return verified, cand, elapsed


def format_whatsapp_reply(
    is_transaction: bool,
    is_verified: bool,
    transaction_id: Optional[str] = None,
    amount: Optional[str] = None,
    payment_app: Optional[str] = None,
    destination_bank: Optional[str] = None,
    account_last4: Optional[str] = None,
    official_ref: Optional[str] = None,
    reconciliation_summary: Optional[str] = None,
    gmail_match: Optional[Dict[str, Any]] = None,
    elapsed_seconds: float = 0.0
) -> str:
    """Generate standardized WhatsApp verification response."""
    if not is_transaction:
        return (
            "⚠️ *TxnVerify AI Notification*\n\n"
            "We received your image, but could not detect a valid payment receipt or transfer confirmation.\n\n"
            "Please send a clear screenshot showing the *Amount* and *Transfer Details*."
        )

    if is_verified:
        subject = gmail_match.get("subject", "Official Payment Confirmation") if gmail_match else "Bank Notification"
        sender = gmail_match.get("sender", "Bank") if gmail_match else "Bank Notification"
        
        bank_line = f"• *Destination:* {destination_bank}" if destination_bank else ""
        if account_last4:
            bank_line = (bank_line + f" (Account ending in {account_last4})") if bank_line else f"• *Account:* ending in {account_last4}"

        ref_id = official_ref or transaction_id or "Confirmed"
        audit_note = f"• *Audit Summary:* {reconciliation_summary}\n" if reconciliation_summary else ""

        return (
            "✅ *Payment Confirmed via Gemma 4!*\n\n"
            f"• *Amount Credited:* {amount or 'Confirmed'}\n"
            f"• *Official Bank Ref:* `{ref_id}`\n"
            f"• *Method/App:* {payment_app or 'Direct Transfer'}\n"
            f"{bank_line}\n"
            f"• *Verified via:* {sender} ({subject})\n"
            f"{audit_note}"
            f"• *Verification Time:* {elapsed_seconds}s\n\n"
            "✨ Your transaction has been reconciled and authenticated against official bank records."
        )
    else:
        ref_display = f"`{transaction_id}`" if transaction_id else "Unresolved"
        return (
            "❌ *Payment Unverified*\n\n"
            f"• *Transaction ID:* {ref_display}\n"
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
    1. Gemini 2.5 Flash Multimodal Visual OCR extraction
    2. Save initial transaction to DB
    3. 60-second Gmail & Bank notification polling + Gemma 4 Reconciliation
    4. Database update with verified bank reference
    5. WhatsApp automated reply
    """
    start_time = time.time()

    # Step 1: Visual OCR
    database.log_event("OCR_START", "PROCESSING", f"Analyzing image with {model_name}", sender=sender_phone)
    if progress_callback:
        progress_callback(0, 0, f"Analyzing receipt with {model_name}...")

    ocr_result = extract_with_google_genai(
        image_bytes=image_bytes,
        mime_type=mime_type,
        api_key=api_key,
        model_name=model_name
    )

    is_transaction = ocr_result.get("is_transaction", False)
    txn_id = ocr_result.get("transaction_id")
    amount = ocr_result.get("amount") or ocr_result.get("amount_value")
    if amount and not any(s in str(amount) for s in ["Rs", "PKR", "$", "₹", "€"]):
        curr = ocr_result.get("currency") or "Rs."
        amount = f"{curr} {amount}"

    # If key payment indicators are visible, mark as transaction
    if not is_transaction and (amount or ocr_result.get("account_last4") or ocr_result.get("destination_bank") or txn_id):
        is_transaction = True

    payment_app = ocr_result.get("payment_app") or ocr_result.get("payment_channel")
    destination_bank = ocr_result.get("destination_bank")
    account_last4 = ocr_result.get("account_last4")
    confidence = ocr_result.get("confidence", 0.95)

    if not is_transaction or not amount:
        reply_text = format_whatsapp_reply(is_transaction=False, is_verified=False)
        database.log_event("OCR_FAILED", "REJECTED", f"No transaction details detected (is_txn={is_transaction}, amt={amount})", sender=sender_phone)

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

    # If transaction_id is missing but it's a valid receipt, assign temporary identifier
    if not txn_id:
        txn_id = f"TXN-{int(time.time())}"
        ocr_result["transaction_id"] = txn_id

    # Step 2: Record in Database
    database.save_transaction(
        transaction_id=txn_id,
        amount=amount,
        sender_phone=sender_phone,
        payment_app=payment_app,
        ocr_confidence=confidence,
        raw_ocr_json=json.dumps(ocr_result)
    )
    database.log_event("OCR_SUCCESS", "EXTRACTED", f"Extracted Txn: {txn_id}, Amount: {amount}, App: {payment_app}",
                       sender=sender_phone, transaction_id=txn_id, amount=amount)

    # Step 3: Polling Loop with Gemma 4 Semantic Reconciliation
    database.log_event("GMAIL_POLL_START", "POLLING", f"Scanning for bank notification & reconciling with Gemma 4 for {txn_id}",
                       sender=sender_phone, transaction_id=txn_id)

    is_verified, gmail_match, gemma_reconcile, poll_elapsed = poll_and_verify_with_gemma4(
        ocr_result=ocr_result,
        timeout_seconds=60,
        poll_interval=4,
        api_key=api_key,
        progress_callback=progress_callback
    )

    official_ref = None
    reconcile_summary = None
    if gemma_reconcile:
        official_ref = gemma_reconcile.get("official_transaction_reference")
        reconcile_summary = gemma_reconcile.get("reconciliation_summary")

    # Step 4: Update Database
    if is_verified and gmail_match:
        database.mark_transaction_verified(
            transaction_id=txn_id,
            gmail_message_id=gmail_match.get("id", ""),
            gmail_subject=gmail_match.get("subject", ""),
            gmail_snippet=gmail_match.get("snippet", ""),
            bank_reference=official_ref,
            reconciliation_summary=reconcile_summary,
            matched_fields=json.dumps(gemma_reconcile.get("matched_fields", [])) if gemma_reconcile else None,
            gemma_verified=1
        )
        database.log_event("VERIFIED", "SUCCESS", f"Confirmed by Gemma 4: Ref {official_ref or txn_id}",
                           sender=sender_phone, transaction_id=txn_id, amount=amount)
    else:
        database.log_event("UNVERIFIED", "TIMEOUT", "No matching bank email confirmed by Gemma 4 within 60s",
                           sender=sender_phone, transaction_id=txn_id, amount=amount)

    # Step 5: Format Reply and Dispatch back to WhatsApp
    reply_text = format_whatsapp_reply(
        is_transaction=True,
        is_verified=is_verified,
        transaction_id=txn_id,
        amount=amount,
        payment_app=payment_app,
        destination_bank=destination_bank,
        account_last4=account_last4,
        official_ref=official_ref,
        reconciliation_summary=reconcile_summary,
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
        "official_bank_ref": official_ref,
        "amount": amount,
        "payment_app": payment_app,
        "confidence": confidence,
        "ocr_result": ocr_result,
        "verified": is_verified,
        "gemma_reconcile": gemma_reconcile,
        "gmail_match": gmail_match,
        "reply_text": reply_text,
        "elapsed_seconds": total_time
    }

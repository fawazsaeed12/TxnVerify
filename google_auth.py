"""
TxnVerify AI - Google OAuth 2.0 & Gmail API Client
Handles Web OAuth flow with gmail.readonly scope, token refresh,
and transactional email polling.
"""

import os
import json
import logging
import base64
import html
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import requests

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import database

logger = logging.getLogger("txnverify.auth")

TOKEN_FILE = Path(__file__).parent / "token.json"
CLIENT_CONFIG_FILE = Path(__file__).parent / "credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")


def get_client_config() -> Dict[str, Any]:
    """Retrieve OAuth client configuration — reads from DB (set via Setup UI) or env vars."""
    if CLIENT_CONFIG_FILE.exists():
        try:
            with open(CLIENT_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    # Read from database (saved via the Setup tab) then fall back to env vars
    client_id     = database.get_config("google_client_id", "") or os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = database.get_config("google_client_secret", "") or os.getenv("GOOGLE_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        raise ValueError(
            "Google OAuth credentials are not configured. "
            "Please complete Step 2 in the Setup tab."
        )

    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI, "http://localhost:8000/oauth2callback"]
        }
    }


def get_google_auth_url(redirect_uri: Optional[str] = None) -> Tuple[str, str]:
    """
    Generate Google OAuth 2.0 authorization URL.
    Returns (authorization_url, state).
    """
    config = get_client_config()
    target_redirect = redirect_uri or REDIRECT_URI

    flow = Flow.from_client_config(
        config,
        scopes=SCOPES,
        redirect_uri=target_redirect
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    database.set_config("oauth_state", state)
    if hasattr(flow, "code_verifier") and flow.code_verifier:
        database.set_config("oauth_code_verifier", flow.code_verifier)
    return auth_url, state


def exchange_code_for_token(code: str, redirect_uri: Optional[str] = None) -> Optional[Credentials]:
    """Exchange authorization code for OAuth credentials and cache them."""
    try:
        config = get_client_config()
        target_redirect = redirect_uri or REDIRECT_URI

        client_info = config.get("web") or config.get("installed", {})
        client_id = client_info.get("client_id")
        client_secret = client_info.get("client_secret")
        token_uri = client_info.get("token_uri", "https://oauth2.googleapis.com/token")

        if not client_id or not client_secret:
            err_msg = "Client ID or Client Secret is missing. Please save Step 2 credentials first."
            database.set_config("last_oauth_error", err_msg)
            database.log_event("AUTH_FAILED", "CONFIG_MISSING", err_msg)
            return None

        code_verifier = database.get_config("oauth_code_verifier")

        # 1. Primary: Use google_auth_oauthlib Flow.fetch_token (handles PKCE code_verifier natively)
        alt_redirect = target_redirect[:-1] if target_redirect.endswith("/") else target_redirect + "/"
        for uri in [target_redirect, alt_redirect]:
            try:
                flow = Flow.from_client_config(config, scopes=SCOPES, redirect_uri=uri)
                if code_verifier:
                    flow.code_verifier = code_verifier
                flow.fetch_token(code=code)
                if flow.credentials:
                    save_credentials(flow.credentials)
                    database.set_config("last_oauth_error", None)
                    database.set_config("oauth_code_verifier", None)
                    database.log_event("AUTH_SUCCESS", "CONNECTED", f"Google OAuth exchange succeeded via Flow ({uri})")
                    return flow.credentials
            except Exception as e_flow:
                logger.warning(f"Flow.fetch_token attempt for {uri} failed: {e_flow}")

        # 2. Fallback: Direct requests.post with code_verifier
        def try_exchange(r_uri: str):
            payload = {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": r_uri,
                "grant_type": "authorization_code"
            }
            if code_verifier:
                payload["code_verifier"] = code_verifier

            return requests.post(
                token_uri,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15
            )

        response = try_exchange(target_redirect)
        if response.status_code != 200 and "redirect_uri_mismatch" in response.text:
            logger.info(f"Retrying token exchange with alternative redirect URI: {alt_redirect}")
            alt_response = try_exchange(alt_redirect)
            if alt_response.status_code == 200:
                response = alt_response

        if response.status_code != 200:
            error_data = {}
            try:
                error_data = response.json()
            except Exception:
                pass
            err_code = error_data.get("error", "oauth_exchange_failed")
            err_desc = error_data.get("error_description", response.text)
            err_summary = f"{err_code}: {err_desc}"

            logger.error(f"Failed to exchange code: {err_summary}")
            database.set_config("last_oauth_error", err_summary)
            database.log_event("AUTH_FAILED", "FAILED", f"Google OAuth failed: {err_summary}")
            return None

        token_data = response.json()
        credentials = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )

        save_credentials(credentials)
        database.set_config("last_oauth_error", None)
        database.set_config("oauth_code_verifier", None)
        database.log_event("AUTH_SUCCESS", "CONNECTED", "Google OAuth exchange succeeded")
        return credentials

    except Exception as e:
        logger.error(f"Error during code exchange: {e}")
        database.set_config("last_oauth_error", str(e))
        database.log_event("AUTH_FAILED", "EXCEPTION", str(e))
        return None


def save_credentials(credentials: Credentials) -> None:
    """Save Google OAuth credentials to token file and DB."""
    cred_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(cred_data, f)
    database.set_config("google_token", cred_data)


def get_stored_credentials() -> Optional[Credentials]:
    """Load valid credentials from token file or database."""
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            logger.warning(f"Failed to load token file: {e}")

    if not creds:
        db_token = database.get_config("google_token")
        if db_token and isinstance(db_token, dict):
            try:
                creds = Credentials.from_authorized_user_info(db_token, SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load DB credentials: {e}")

    if creds:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                save_credentials(creds)
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                return None
        return creds

    return None


def get_user_email() -> Optional[str]:
    """Retrieve the signed-in user's Google email."""
    creds = get_stored_credentials()
    if not creds or not creds.valid:
        return None

    try:
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress")
    except Exception as e:
        logger.warning(f"Could not fetch user profile: {e}")
        return "Connected Google Account"


def extract_body_from_payload(payload: Dict[str, Any]) -> str:
    """Recursively extract plain text or decoded HTML from Gmail message payload."""
    text_parts = []

    def _walk_parts(p):
        mime_type = p.get("mimeType", "")
        body_data = p.get("body", {}).get("data")

        if mime_type == "text/plain" and body_data:
            try:
                decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                text_parts.append(decoded)
                return
            except Exception:
                pass

        if mime_type == "text/html" and body_data:
            try:
                decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                clean = re.sub(r"<[^>]+>", " ", decoded)
                clean = html.unescape(clean)
                clean = re.sub(r"\s+", " ", clean).strip()
                text_parts.append(clean)
            except Exception:
                pass

        for subpart in p.get("parts", []):
            _walk_parts(subpart)

    _walk_parts(payload)
    return "\n".join(text_parts).strip()


def query_candidate_emails(extracted_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Search both live Gmail and local bank store for candidate transaction emails.
    Uses multi-faceted query strategy (amount, account last4, destination bank, channel, transaction ID).
    """
    candidates = []
    seen_ids = set()

    # Extract search keywords from OCR metadata
    amount_str = str(extracted_info.get("amount") or "")
    amount_val = str(extracted_info.get("amount_value") or "")
    if not amount_val and amount_str:
        amt_match = re.search(r"(\d+(?:\.\d{1,2})?)", amount_str)
        if amt_match:
            amount_val = amt_match.group(1)

    last4 = str(extracted_info.get("account_last4") or "").strip()
    bank = str(extracted_info.get("destination_bank") or "").strip()
    channel = str(extracted_info.get("payment_channel") or "").strip()
    txn_id = str(extracted_info.get("transaction_id") or "").strip()

    # 1. Search Live Gmail API if credentials exist
    creds = get_stored_credentials()
    if creds and creds.valid:
        try:
            service = build("gmail", "v1", credentials=creds)

            # Build query variants to find the bank notification
            queries = []
            if txn_id and len(txn_id) <= 32:
                queries.append(f'"{txn_id}"')

            if amount_val:
                queries.append(f'"{amount_val}" (credit OR credited OR received OR transfer OR deposit OR RAAST) newer_than:3d')
                if last4:
                    queries.append(f'"{amount_val}" "{last4}" newer_than:3d')

            if bank or channel:
                queries.append(f'({bank or channel} OR RAAST OR "Fund Transfer") newer_than:2d')

            queries.append('(credit OR credited OR "Fund Transfer" OR "RAAST Fund Transfer") newer_than:2d')

            for q in queries:
                try:
                    resp = service.users().messages().list(userId="me", q=q, maxResults=5).execute()
                    msg_items = resp.get("messages", [])
                    for item in msg_items:
                        mid = item["id"]
                        if mid in seen_ids:
                            continue
                        seen_ids.add(mid)

                        msg = service.users().messages().get(userId="me", id=mid, format="full").execute()
                        payload = msg.get("payload", {})
                        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
                        body = extract_body_from_payload(payload) or msg.get("snippet", "")

                        candidates.append({
                            "id": mid,
                            "threadId": msg.get("threadId"),
                            "snippet": msg.get("snippet", ""),
                            "body": body,
                            "subject": headers.get("Subject", "Payment Notification"),
                            "sender": headers.get("From", "Bank Alert"),
                            "date": headers.get("Date", ""),
                            "source": "Live Gmail API"
                        })
                        if len(candidates) >= 6:
                            break
                except HttpError as he:
                    if "accessNotConfigured" in str(he) or "disabled" in str(he):
                        logger.warning("Gmail API is disabled in Google Cloud Console. Enable Gmail API to poll live inbox.")
                        database.set_config("last_oauth_error", "Gmail API is not yet enabled in your Google Cloud Project. Please enable it in Google Cloud Console.")
                        break
                    else:
                        logger.warning(f"Gmail query error for '{q}': {he}")
                if len(candidates) >= 6:
                    break

        except Exception as e:
            logger.warning(f"Error querying live Gmail: {e}")

    # 2. Search Database Bank Store
    db_terms = [t for t in [txn_id, amount_val, last4, bank, channel] if t]
    if not db_terms and amount_str:
        db_terms.append(amount_str)

    local_matches = database.search_bank_emails(db_terms)
    for row in local_matches:
        mid = f"db-{row['id']}"
        if mid not in seen_ids:
            seen_ids.add(mid)
            candidates.append({
                "id": mid,
                "threadId": f"thread-{row['id']}",
                "snippet": row.get("body", "")[:200],
                "body": row.get("body", ""),
                "subject": row.get("subject", ""),
                "sender": row.get("sender", ""),
                "date": row.get("received_at", ""),
                "source": "Bank Notification Mail Store"
            })

    return candidates


def query_gmail_for_transaction(transaction_id: str) -> Optional[Dict[str, Any]]:
    """
    Search Gmail messages for transaction_id.
    Returns matched message dictionary with subject, snippet, id, or None.
    """
    candidates = query_candidate_emails({"transaction_id": transaction_id})
    return candidates[0] if candidates else None


def sign_out() -> None:
    """Clear all stored credentials."""
    if TOKEN_FILE.exists():
        try:
            TOKEN_FILE.unlink()
        except Exception:
            pass
    database.set_config("google_token", None)

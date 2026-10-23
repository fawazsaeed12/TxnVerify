"""
TxnVerify AI - Google OAuth 2.0 & Gmail API Client
Handles Web OAuth flow with gmail.readonly scope, token refresh,
and transactional email polling.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
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

        # Helper to attempt token exchange with a specific redirect URI
        def try_exchange(r_uri: str):
            return requests.post(
                token_uri,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": r_uri,
                    "grant_type": "authorization_code"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15
            )

        # First attempt with requested redirect URI
        response = try_exchange(target_redirect)

        # If Google reports redirect_uri_mismatch, try alternate formatting (trailing slash vs no slash)
        if response.status_code != 200 and "redirect_uri_mismatch" in response.text:
            alt_redirect = target_redirect[:-1] if target_redirect.endswith("/") else target_redirect + "/"
            logger.info(f"Retrying token exchange with alternative redirect URI: {alt_redirect}")
            alt_response = try_exchange(alt_redirect)
            if alt_response.status_code == 200:
                response = alt_response
                target_redirect = alt_redirect

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


def query_gmail_for_transaction(transaction_id: str) -> Optional[Dict[str, Any]]:
    """
    Search Gmail messages for transaction_id.
    Returns matched message dictionary with subject, snippet, id, or None.
    """
    creds = get_stored_credentials()
    if not creds or not creds.valid:
        # No live credentials — fall back to the local mock-email table
        # (populated by generate_sample_receipt.py for offline testing)
        matches = database.search_mock_emails(transaction_id)
        if matches:
            top = matches[0]
            return {
                "id": f"mock-{top['id']}",
                "threadId": f"mock-thread-{top['id']}",
                "snippet": top["body"][:200],
                "subject": top["subject"],
                "sender": top["sender"],
                "source": "Local test data (no Gmail connected)"
            }
        return None

    try:
        service = build("gmail", "v1", credentials=creds)
        # Search query matching transaction ID in query string
        query = f'"{transaction_id}"'
        results = service.users().messages().list(userId="me", q=query, maxResults=5).execute()
        messages = results.get("messages", [])

        if not messages:
            # Fallback search without quotes
            results = service.users().messages().list(userId="me", q=transaction_id, maxResults=5).execute()
            messages = results.get("messages", [])

        if not messages:
            return None

        # Fetch the first matched message details
        msg_id = messages[0]["id"]
        msg = service.users().messages().get(userId="me", id=msg_id, format="metadata",
                                             metadataHeaders=["Subject", "From", "Date"]).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        return {
            "id": msg_id,
            "threadId": msg.get("threadId"),
            "snippet": msg.get("snippet", ""),
            "subject": headers.get("Subject", "Payment Notification"),
            "sender": headers.get("From", "Bank Notification"),
            "date": headers.get("Date", ""),
            "source": "Live Gmail API"
        }

    except HttpError as error:
        logger.error(f"Gmail API HTTP error: {error}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error searching Gmail: {e}")
        return None


def sign_out() -> None:
    """Clear all stored credentials."""
    if TOKEN_FILE.exists():
        try:
            TOKEN_FILE.unlink()
        except Exception:
            pass
    database.set_config("google_token", None)

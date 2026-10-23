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

# Default developer app credentials for hackathon demonstration.
# Users can also override these via environment variables or the UI.
DEFAULT_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "1083921849182-demo-txnverify.apps.googleusercontent.com")
DEFAULT_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "GOCSPX-demoTxnVerifyClientSecret123")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")


def get_client_config() -> Dict[str, Any]:
    """Retrieve OAuth client configuration."""
    if CLIENT_CONFIG_FILE.exists():
        try:
            with open(CLIENT_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    client_id = os.getenv("GOOGLE_CLIENT_ID", database.get_config("google_client_id", DEFAULT_CLIENT_ID))
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", database.get_config("google_client_secret", DEFAULT_CLIENT_SECRET))

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

        # Make token request directly
        response = requests.post(
            token_uri,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": target_redirect,
                "grant_type": "authorization_code"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code != 200:
            logger.error(f"Failed to exchange code: {response.text}")
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
        return credentials

    except Exception as e:
        logger.error(f"Error during code exchange: {e}")
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
    # Check if sandbox demo mode is active
    if database.get_config("sandbox_mode", False):
        return database.get_config("sandbox_email", "judge-demo@txnverify.ai (Sandbox Mode)")

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
    # 1. First check if Sandbox Demo mode is enabled or if mock email matches
    if database.get_config("sandbox_mode", False):
        matches = database.search_mock_emails(transaction_id)
        if matches:
            top = matches[0]
            return {
                "id": f"mock-{top['id']}",
                "threadId": f"mock-thread-{top['id']}",
                "snippet": top["body"][:200],
                "subject": top["subject"],
                "sender": top["sender"],
                "source": "Sandbox Mock Bank Inbox"
            }

    # 2. Query real Gmail API
    creds = get_stored_credentials()
    if not creds or not creds.valid:
        # If real Gmail not authenticated, also check mock emails table as fallback
        matches = database.search_mock_emails(transaction_id)
        if matches:
            top = matches[0]
            return {
                "id": f"mock-{top['id']}",
                "threadId": f"mock-thread-{top['id']}",
                "snippet": top["body"][:200],
                "subject": top["subject"],
                "sender": top["sender"],
                "source": "Mock Bank Inbox (Fallback)"
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
    """Clear credentials."""
    if TOKEN_FILE.exists():
        try:
            TOKEN_FILE.unlink()
        except Exception:
            pass
    database.set_config("google_token", None)
    database.set_config("sandbox_mode", False)

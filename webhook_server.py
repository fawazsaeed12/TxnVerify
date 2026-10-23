"""
TxnVerify AI - FastAPI Webhook & Processing Server
Receives incoming payment screenshots forwarded by the WhatsApp Gateway,
runs the Gemma 4 visual OCR and Gmail verification pipeline,
and provides REST APIs for the Streamlit dashboard.
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, BackgroundTasks, Request, Query, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

import database
import agent_core
import google_auth

logger = logging.getLogger("txnverify.server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(title="TxnVerify AI Webhook Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WhatsAppMediaPayload(BaseModel):
    from_: str = Field(alias="from")
    sender_name: Optional[str] = "WhatsApp User"
    body: Optional[str] = ""
    timestamp: Optional[int] = None
    mimetype: str = "image/jpeg"
    data: str  # Base64 encoded image string
    filename: Optional[str] = "receipt.jpg"

    class Config:
        populate_by_name = True


class DirectVerifyRequest(BaseModel):
    image_base64: str
    mime_type: Optional[str] = "image/jpeg"
    sender_phone: Optional[str] = "judge_test_panel"
    gemini_api_key: Optional[str] = None
    model_name: Optional[str] = None


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "TxnVerify AI Webhook Server",
        "agent_running": database.get_config("agent_running", True),
        "user_email": google_auth.get_user_email()
    }


def background_process_receipt(image_bytes: bytes, mime_type: str, sender: str):
    """Run verification in background thread."""
    try:
        agent_core.process_payment_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            sender_phone=sender
        )
    except Exception as e:
        logger.error(f"Error in background payment verification: {e}")
        database.log_event("PIPELINE_ERROR", "ERROR", str(e), sender=sender)


@app.post("/webhook/whatsapp")
async def receive_whatsapp_media(payload: WhatsAppMediaPayload, background_tasks: BackgroundTasks):
    """
    Primary webhook receiving forwarded payment screenshots from whatsapp_gateway.js.
    """
    logger.info(f"Received media message from: {payload.from_} ({payload.mimetype})")

    # Check if agent is enabled
    is_running = database.get_config("agent_running", True)
    if not is_running:
        logger.info("Agent is currently paused/stopped. Skipping processing.")
        return JSONResponse(content={"status": "SKIPPED", "reason": "Agent is stopped by user"})

    try:
        # Decode base64 image
        image_bytes = base64.b64decode(payload.data)
    except Exception as e:
        logger.error(f"Invalid base64 payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    # Run processing asynchronously to immediately return 200 OK to the gateway
    background_tasks.add_task(
        background_process_receipt,
        image_bytes=image_bytes,
        mime_type=payload.mimetype,
        sender=payload.from_
    )

    return JSONResponse(content={
        "status": "QUEUED",
        "message": "Payment screenshot queued for Gemma 4 extraction and Gmail verification",
        "sender": payload.from_
    })


@app.post("/api/verify-direct")
def direct_verify(request: DirectVerifyRequest):
    """
    Direct synchronous endpoint used by the Streamlit Judge Test Panel.
    """
    try:
        image_bytes = base64.b64decode(request.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {e}")

    result = agent_core.process_payment_image(
        image_bytes=image_bytes,
        mime_type=request.mime_type or "image/jpeg",
        sender_phone=request.sender_phone,
        api_key=request.gemini_api_key,
        model_name=request.model_name or agent_core.DEFAULT_MODEL
    )
    return result


@app.get("/oauth2callback")
def oauth_callback(code: Optional[str] = None, error: Optional[str] = None):
    """
    OAuth 2.0 redirect handler from Google.
    Exchanges code for tokens and redirects back to Streamlit dashboard.
    """
    if error:
        return JSONResponse(status_code=400, content={"error": error})
    if not code:
        return JSONResponse(status_code=400, content={"error": "Missing authorization code"})

    creds = google_auth.exchange_code_for_token(code, redirect_uri="http://localhost:8000/oauth2callback")
    if creds:
        database.log_event("AUTH_SUCCESS", "CONNECTED", "Google Account connected successfully via OAuth 2.0")
        # Redirect back to Streamlit UI
        return RedirectResponse(url="http://localhost:8501/?auth_success=true")
    else:
        return JSONResponse(status_code=500, content={"error": "Token exchange failed"})


@app.get("/api/logs")
def get_logs(limit: int = 50):
    """Retrieve activity logs."""
    return database.get_recent_logs(limit)


@app.get("/api/transactions")
def get_transactions(limit: int = 50):
    """Retrieve processed transactions."""
    return database.get_transactions(limit)


if __name__ == "__main__":
    port = int(os.getenv("FASTAPI_PORT", 8000))
    print(f"Starting TxnVerify AI Webhook Server on port {port}...")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

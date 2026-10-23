import json
import database
import google_auth
from google import genai
from google.genai import types

# 1. Test image
img_path = r'C:\Users\fawaz\.gemini\antigravity\brain\d913004b-31b3-4848-b401-e6b475d92d17\.user_uploaded\media_1792769541312_38fdab95.png'
img_bytes = open(img_path, 'rb').read()

api_key = database.get_config('gemini_api_key')
client = genai.Client(api_key=api_key)

# 2. Extract with gemini-2.5-flash
part = types.Part.from_bytes(data=img_bytes, mime_type='image/png')
prompt = """Analyze this payment screenshot. Return a JSON object with:
{
  "is_transaction": true,
  "transaction_id": "alphanumeric string or hash",
  "amount": "amount string with symbol or code, e.g. Rs. 100",
  "amount_value": "numeric value, e.g. 100",
  "currency": "PKR or Rs",
  "sender_name": "sender title",
  "receiver_name": "destination title",
  "account_last4": "last 4 digits of account if present",
  "destination_bank": "bank name",
  "payment_channel": "e.g. Raast, IMPS, Zelle",
  "payment_app": "e.g. NayaPay, SadaPay, Easypaisa",
  "timestamp": "e.g. 23 Oct 2026, 08:30 PM"
}
Output raw JSON only."""

res = client.models.generate_content(model='gemini-2.5-flash', contents=[part, prompt])
print("=== EXTRACTED OCR VIA GEMINI 2.5 FLASH ===")
clean_text = res.text.strip().replace("```json", "").replace("```", "").strip()
print(clean_text)
ocr_data = json.loads(clean_text)

# 3. Query candidates
candidates = database.search_mock_emails("")
print(f"\nFound {len(candidates)} emails in database store.")

# Filter candidates matching amount or bank or last4
matching_cand = None
for c in candidates:
    body = c['body']
    if '3206' in body or '100' in body or 'RAAST' in body:
        matching_cand = c
        break

print("\nSelected candidate email subject:", matching_cand['subject'])

# 4. Reconcile with Gemma 4
gemma_prompt = f"""You are TxnVerify AI's core fraud-detection and reconciliation engine powered by Gemma 4.
Your task is to reconcile and verify a customer's payment screenshot against an official bank notification email.

Customer Receipt Data (Extracted from image):
{json.dumps(ocr_data, indent=2)}

Bank Notification Email Content:
Subject: {matching_cand['subject']}
From: {matching_cand['sender']}
Body:
{matching_cand['body']}

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

gemma_res = client.models.generate_content(model='gemma-4-26b-a4b-it', contents=gemma_prompt)
print("\n=== GEMMA 4 RECONCILIATION RESULT ===")
print(gemma_res.text)

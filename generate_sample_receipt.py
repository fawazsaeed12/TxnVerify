"""
TxnVerify AI - Sample Receipt Generator & Test Suite
Generates realistic payment confirmation receipts (Zelle, Venmo, UPI, Chase)
and adds corresponding mock confirmation emails for Hackathon Judges to test instantly.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import database

SAMPLE_DIR = Path(__file__).parent / "sample_receipts"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def create_receipt_image(
    filename: str,
    app_name: str,
    amount: str,
    txn_id: str,
    recipient: str,
    bg_color: str,
    accent_color: str
) -> Path:
    """Create a realistic clean receipt image."""
    width, height = 480, 700
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Header Card
    draw.rectangle([(0, 0), (width, 140)], fill=accent_color)

    # Use default bitmap font (guaranteed to work cross-platform without TTF dependency)
    # Check mark circle
    draw.ellipse([(width // 2 - 30, 40), (width // 2 + 30, 100)], fill="white")
    draw.line([(width // 2 - 14, 70), (width // 2 - 4, 82), (width // 2 + 14, 58)], fill=accent_color, width=4)

    # Status & Amount
    draw.text((width // 2 - 70, 160), "Payment Successful", fill="#1e293b")
    draw.text((width // 2 - 60, 210), amount, fill="#0f172a")

    # Divider
    draw.line([(40, 280), (width - 40, 280)], fill="#e2e8f0", width=2)

    # Details Section
    details = [
        ("Platform", app_name),
        ("To", recipient),
        ("Transaction ID", txn_id),
        ("Date & Time", "Today, 18:45"),
        ("Status", "Completed"),
        ("Payment Type", "Direct Transfer")
    ]

    y = 310
    for label, val in details:
        draw.text((45, y), label, fill="#64748b")
        draw.text((width - 45 - len(val) * 7, y), val, fill="#0f172a")
        y += 45

    # Footer banner
    draw.rectangle([(40, 600), (width - 40, 660)], fill="#f1f5f9", outline="#cbd5e1")
    draw.text((65, 625), f"Official {app_name} Electronic Receipt • Ref verified", fill="#475569")

    out_path = SAMPLE_DIR / filename
    img.save(out_path, "JPEG", quality=95)
    return out_path


def seed_sample_receipts_and_mock_emails():
    """Create 3 diverse sample receipts and matching bank mock confirmation emails."""
    samples = [
        {
            "filename": "zelle_receipt_150.jpg",
            "app_name": "Zelle",
            "amount": "$150.00",
            "txn_id": "ZEL-982341908",
            "recipient": "Sarah Miller",
            "bg_color": "#ffffff",
            "accent_color": "#7414ca",
            "email_sender": "customerservice@chase.com",
            "email_subject": "Chase Alert: You received $150.00 with Zelle (Ref ZEL-982341908)",
            "email_body": "Hello, Sarah Miller sent you $150.00 using Zelle. Transaction reference number ZEL-982341908. Funds are available now in your checking account."
        },
        {
            "filename": "venmo_receipt_45.jpg",
            "app_name": "Venmo",
            "amount": "$45.00",
            "txn_id": "VEN-549102834",
            "recipient": "Alex Johnson",
            "bg_color": "#ffffff",
            "accent_color": "#008cff",
            "email_sender": "venmo@venmo.com",
            "email_subject": "Alex Johnson paid you $45.00 (Txn VEN-549102834)",
            "email_body": "You received a payment of $45.00 from Alex Johnson on Venmo. Reference ID: VEN-549102834. Note: Dinner split."
        },
        {
            "filename": "upi_receipt_2500.jpg",
            "app_name": "Google Pay UPI",
            "amount": "₹2,500.00",
            "txn_id": "UPI-409182390192",
            "recipient": "Aarav Sharma",
            "bg_color": "#ffffff",
            "accent_color": "#1a73e8",
            "email_sender": "alerts@hdfcbank.net",
            "email_subject": "HDFC Bank Alert: UPI Credit of Rs 2,500.00 Ref UPI-409182390192",
            "email_body": "Dear Customer, INR 2,500.00 has been credited to your A/c via UPI from Aarav Sharma. UPI Ref No UPI-409182390192 on 23-Oct."
        }
    ]

    for item in samples:
        path = create_receipt_image(
            filename=item["filename"],
            app_name=item["app_name"],
            amount=item["amount"],
            txn_id=item["txn_id"],
            recipient=item["recipient"],
            bg_color=item["bg_color"],
            accent_color=item["accent_color"]
        )
        print(f"Generated sample receipt: {path}")

        # Seed mock email
        database.add_mock_email(
            sender=item["email_sender"],
            subject=item["email_subject"],
            body=item["email_body"],
            transaction_id=item["txn_id"],
            amount=item["amount"]
        )
        print(f"Seeded mock bank confirmation email for Txn ID: {item['txn_id']}")


if __name__ == "__main__":
    seed_sample_receipts_and_mock_emails()
    print("All sample receipts and mock inbox entries created successfully!")

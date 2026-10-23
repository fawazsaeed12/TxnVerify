"""
TxnVerify AI - Automated Verification Pipeline Test
Tests end-to-end database transactions, mock Gmail search,
and receipt parsing logic.
"""

import database
import google_auth
import agent_core

def run_tests():
    print("Testing TxnVerify AI Core Pipeline...")

    # 1. Test database logging
    log_id = database.log_event("TEST_EVENT", "OK", "Testing DB logging function", sender="test_suite")
    assert log_id > 0, "Log insertion failed"
    print(" [1/4] SQLite logging: PASSED")

    # 2. Test mock Gmail matching in sandbox mode
    database.set_config("sandbox_mode", True)
    test_txn_id = "ZEL-982341908"
    match = google_auth.query_gmail_for_transaction(test_txn_id)
    assert match is not None, f"Failed to match seeded transaction: {test_txn_id}"
    assert test_txn_id in match["subject"] or test_txn_id in match["snippet"], "Mismatch in transaction ID"
    print(f" [2/4] Mock Gmail transaction query ({test_txn_id}): PASSED")

    # 3. Test polling verification loop (short timeout)
    is_verified, email_match, elapsed = agent_core.poll_gmail_for_transaction(
        transaction_id=test_txn_id,
        timeout_seconds=5,
        poll_interval=1
    )
    assert is_verified is True, "Polling verification failed on seeded transaction"
    print(f" [3/4] 60s Polling Loop simulator ({elapsed}s elapsed): PASSED")

    # 4. Test WhatsApp reply generator
    reply = agent_core.format_whatsapp_reply(
        is_transaction=True,
        is_verified=True,
        transaction_id=test_txn_id,
        amount="$150.00",
        payment_app="Zelle",
        gmail_match=email_match,
        elapsed_seconds=elapsed
    )
    assert "Payment Confirmed" in reply, "Reply missing confirmation text"
    assert test_txn_id in reply, "Reply missing transaction ID"
    print(" [4/4] WhatsApp response template formatting: PASSED")

    print("\n All core engine tests passed successfully!")

if __name__ == "__main__":
    run_tests()

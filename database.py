"""
TxnVerify AI - SQLite Database Layer
Stores activity logs, verified transactions, mock Gmail emails for judges,
and agent runtime configurations.
"""

import sqlite3
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

DB_PATH = Path(__file__).parent / "txnverify.db"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables with schema."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Activity logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                sender TEXT,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                transaction_id TEXT,
                amount TEXT
            )
        """)

        # Verified transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                amount TEXT,
                sender_phone TEXT,
                payment_app TEXT,
                ocr_confidence REAL,
                gmail_verified INTEGER DEFAULT 0,
                gemma_verified INTEGER DEFAULT 0,
                bank_reference TEXT,
                reconciliation_summary TEXT,
                matched_fields TEXT,
                gmail_message_id TEXT,
                gmail_subject TEXT,
                gmail_snippet TEXT,
                created_at TEXT NOT NULL,
                verified_at TEXT,
                raw_ocr_json TEXT
            )
        """)

        # Migration: add newer columns if table was created earlier
        existing_cols = [c[1] for c in cursor.execute("PRAGMA table_info(transactions)").fetchall()]
        for col_name, col_def in [
            ("gemma_verified", "INTEGER DEFAULT 0"),
            ("bank_reference", "TEXT"),
            ("reconciliation_summary", "TEXT"),
            ("matched_fields", "TEXT")
        ]:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col_name} {col_def}")
                except Exception:
                    pass

        # Mock / Sandbox emails table (allows judges to simulate bank confirmation emails)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                amount TEXT,
                received_at TEXT NOT NULL
            )
        """)

        # System configurations & session tokens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.commit()


def log_event(event_type: str, status: str, details: str = "", sender: Optional[str] = None,
              transaction_id: Optional[str] = None, amount: Optional[str] = None) -> int:
    """Log an event to the activity_logs table."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity_logs (timestamp, sender, event_type, status, details, transaction_id, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (now, sender, event_type, status, details, transaction_id, amount))
        conn.commit()
        return cursor.lastrowid


def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent activity logs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM activity_logs ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def save_transaction(transaction_id: str, amount: Optional[str] = None,
                     sender_phone: Optional[str] = None, payment_app: Optional[str] = None,
                     ocr_confidence: float = 1.0, raw_ocr_json: Optional[str] = None) -> int:
    """Insert or update a transaction record."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (transaction_id, amount, sender_phone, payment_app, ocr_confidence, created_at, raw_ocr_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(transaction_id) DO UPDATE SET
                amount=excluded.amount,
                sender_phone=excluded.sender_phone,
                payment_app=excluded.payment_app,
                ocr_confidence=excluded.ocr_confidence,
                raw_ocr_json=excluded.raw_ocr_json
        """, (transaction_id, amount, sender_phone, payment_app, ocr_confidence, now, raw_ocr_json))
        conn.commit()
        return cursor.lastrowid


def mark_transaction_verified(
    transaction_id: str,
    gmail_message_id: str = "",
    gmail_subject: str = "",
    gmail_snippet: str = "",
    bank_reference: Optional[str] = None,
    reconciliation_summary: Optional[str] = None,
    matched_fields: Optional[str] = None,
    gemma_verified: int = 1
) -> None:
    """Mark transaction as successfully verified via Gemma 4 and Gmail."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE transactions
            SET gmail_verified = 1,
                gemma_verified = ?,
                bank_reference = ?,
                reconciliation_summary = ?,
                matched_fields = ?,
                gmail_message_id = ?,
                gmail_subject = ?,
                gmail_snippet = ?,
                verified_at = ?
            WHERE transaction_id = ?
        """, (
            gemma_verified,
            bank_reference,
            reconciliation_summary,
            matched_fields,
            gmail_message_id,
            gmail_subject,
            gmail_snippet,
            now,
            transaction_id
        ))
        conn.commit()


def get_transactions(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve all processed transactions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM transactions ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def set_config(key: str, value: Any) -> None:
    """Save key-value configuration."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    val_str = json.dumps(value) if not isinstance(value, str) else value
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO system_config (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
        """, (key, val_str, now))
        conn.commit()


def get_config(key: str, default: Any = None) -> Any:
    """Get key-value configuration."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        if not row:
            return default
        val = row["value"]
        try:
            return json.loads(val)
        except Exception:
            return val


def add_mock_email(sender: str, subject: str, body: str, transaction_id: str, amount: str = "") -> int:
    """Add a mock transaction confirmation email for testing."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mock_emails (sender, subject, body, transaction_id, amount, received_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sender, subject, body, transaction_id, amount, now))
        conn.commit()
        return cursor.lastrowid


def search_mock_emails(transaction_id: str) -> List[Dict[str, Any]]:
    """Search mock emails by transaction_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM mock_emails
            WHERE transaction_id LIKE ? OR body LIKE ? OR subject LIKE ?
            ORDER BY id DESC
        """, (f"%{transaction_id}%", f"%{transaction_id}%", f"%{transaction_id}%"))
        return [dict(row) for row in cursor.fetchall()]


def search_bank_emails(terms: List[str]) -> List[Dict[str, Any]]:
    """Search mock/stored bank emails using multiple search keywords."""
    valid_terms = [t.strip() for t in terms if t and len(str(t).strip()) >= 2]
    if not valid_terms:
        return search_mock_emails("")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        conditions = []
        params = []
        for t in valid_terms:
            t_clean = f"%{t}%"
            conditions.append("(transaction_id LIKE ? OR body LIKE ? OR subject LIKE ?)")
            params.extend([t_clean, t_clean, t_clean])

        query = f"""
            SELECT * FROM mock_emails
            WHERE {" OR ".join(conditions)}
            ORDER BY id DESC
        """
        cursor.execute(query, params)
        rows = cursor.fetchall()
        seen = set()
        deduped = []
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                deduped.append(dict(r))
        return deduped


# Auto-initialize database on import
init_db()
